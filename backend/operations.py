"""Tenant-bound automation contracts and a provider-free WhatsApp rehearsal."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException, Request
from pydantic import Field

from . import db
from .domain import book, create_lead, match_properties, require
from .models import Booking, Model
from .security import admin, current_user

router = APIRouter()


def set_handoff(c, tenant, lead_id, active, reason, actor):
    require(c, 'leads', tenant, lead_id)
    c.execute('INSERT INTO conversation_controls VALUES(?,?,?,?,?) ON CONFLICT(lead_id) DO UPDATE SET human_active=excluded.human_active,reason=excluded.reason,updated_at=excluded.updated_at',
              (lead_id, tenant, int(active), reason if active else '', db.now()))
    if active:
        exists = c.execute("SELECT 1 FROM tasks WHERE tenant_id=? AND lead_id=? AND kind='handoff' AND status='Pending'", (tenant, lead_id)).fetchone()
        if not exists:
            c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)', (db.uid(), tenant, lead_id, 'Human adviser requested', db.now(), 'Pending', 'handoff', db.now()))
        c.execute("UPDATE outbox SET status='Held',error='Human adviser owns conversation' WHERE tenant_id=? AND lead_id=? AND status IN ('Pending','Retry') AND dedupe_key NOT LIKE 'manual:%' AND template=''", (tenant, lead_id))
    else:
        c.execute("UPDATE tasks SET status='Completed' WHERE tenant_id=? AND lead_id=? AND kind='handoff' AND status='Pending'", (tenant, lead_id))
    db.audit(c, tenant, actor, 'conversation.handoff' if active else 'conversation.resumed', lead_id, reason if active else '')


def lead_intelligence(c, tenant, lead_id):
    lead = require(c, 'leads', tenant, lead_id)
    control = c.execute('SELECT human_active FROM conversation_controls WHERE tenant_id=? AND lead_id=?', (tenant, lead_id)).fetchone()
    inbound = c.execute("SELECT body,created_at FROM messages WHERE tenant_id=? AND lead_id=? AND direction='inbound' ORDER BY created_at DESC LIMIT 1", (tenant, lead_id)).fetchone()
    text = inbound['body'].casefold() if inbound else ''
    booking_intent = any(word in text for word in ('viewing', 'appointment', 'book', 'معاينة', 'معاينه', 'احجز', 'موعد'))
    human = bool(control and control['human_active'])
    recent = bool(inbound and datetime.fromisoformat(inbound['created_at']) > datetime.now(timezone.utc) - timedelta(hours=24))
    allowed = bool(lead['consent'] and not lead['opted_out'] and not human)
    matches = match_properties(c, tenant, lead)
    missing = [key for key in ('budget', 'location', 'property_type') if not lead[key]]
    return {'lead_id': lead_id, 'intent': 'human_handoff' if human else 'appointment' if booking_intent else lead['intent'],
            'score': lead['score'], 'stage': lead['stage'], 'missing_fields': missing,
            'assigned_agent_id': lead['assigned_to'], 'human_active': human,
            'recommendations': [{'id': p['id'], 'title': p['title'], 'price': p['price'], 'match_score': p['match_score'], 'reasons': p['reasons']} for p in matches],
            'consent': bool(lead['consent']), 'opted_out': bool(lead['opted_out']),
            'service_window_open': recent, 'followup_eligible': allowed,
            'template_required': lead['source'] == 'whatsapp' and not recent,
            'next_action': 'human_adviser' if human else 'respect_opt_out' if lead['opted_out'] else 'qualify' if missing else 'review_inventory' if not matches else 'offer_viewing',
            'method': 'Recorded preferences, latest message intent and live inventory; rule-based, no paid inference'}


class LeadReference(Model):
    lead_id: str = Field(min_length=1, max_length=100)


class HandoffInput(Model):
    active: bool = True
    reason: Literal['Customer requested an adviser', 'Operator takeover', 'Qualification escalation'] = 'Operator takeover'


class BridgeHandoff(LeadReference, HandoffInput):
    pass


@router.get('/api/leads/{lead_id}/intelligence')
def intelligence(lead_id: str, user=Depends(current_user)):
    with db.connection() as c:
        return lead_intelligence(c, user['tenant_id'], lead_id)


@router.post('/api/leads/{lead_id}/handoff')
def handoff(lead_id: str, data: HandoffInput, user=Depends(current_user)):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        set_handoff(c, user['tenant_id'], lead_id, data.active, data.reason, user['id'])
    return {'human_active': data.active}


def bridge_tenant(request, c):
    from .integrations import bearer, integration_tenant
    bearer(request, 'MADAR_BRIDGE_TOKEN')
    return integration_tenant(c)


@router.post('/api/bridge/intelligence')
def bridge_intelligence(data: LeadReference, request: Request):
    with db.connection() as c:
        return lead_intelligence(c, bridge_tenant(request, c), data.lead_id)


@router.post('/api/bridge/handoff')
def bridge_handoff(data: BridgeHandoff, request: Request):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = bridge_tenant(request, c)
        set_handoff(c, tenant, data.lead_id, data.active, data.reason, 'n8n')
    return {'lead_id': data.lead_id, 'human_active': data.active}


class BookingEvent(Model):
    event_id: str = Field(min_length=1, max_length=200)
    appointment: Booking


@router.post('/api/bridge/appointments')
def bridge_book(data: BookingEvent, request: Request):
    body = data.appointment.model_dump()
    signature = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = bridge_tenant(request, c)
        key = 'booking:' + data.event_id
        prior = c.execute('SELECT * FROM automation_receipts WHERE tenant_id=? AND event_id=?', (tenant, key)).fetchone()
        if prior:
            if prior['request_hash'] != signature:
                raise HTTPException(409, 'Event ID was previously used for a different booking')
            return dict(json.loads(prior['result']), duplicate=True)
        result = {'appointment': book(c, tenant, body, 'n8n'), 'duplicate': False}
        c.execute('INSERT INTO automation_receipts VALUES(?,?,?,?,?)', (tenant, key, signature, json.dumps(result), db.now()))
    return result


@router.post('/api/bridge/report')
def bridge_report(request: Request):
    from .main import report
    with db.connection() as c:
        tenant = bridge_tenant(request, c)
    return report({'tenant_id': tenant})


def operation_status(c, tenant):
    counts = {r['status']: r['total'] for r in c.execute('SELECT status,COUNT(*) AS total FROM outbox WHERE tenant_id=? GROUP BY status', (tenant,))}
    return {'external_send_enabled': os.getenv('MADAR_ALLOW_EXTERNAL_SEND') == 'true',
            'model_usage_enabled': os.getenv('MADAR_ALLOW_MODEL_USAGE') == 'true',
            'outbox': counts, 'open_incidents': c.execute("SELECT COUNT(*) FROM incidents WHERE tenant_id=? AND status='Open'", (tenant,)).fetchone()[0],
            'human_handoffs': c.execute('SELECT COUNT(*) FROM conversation_controls WHERE tenant_id=? AND human_active=1', (tenant,)).fetchone()[0],
            'n8n_runtime': 'NOT VERIFIED', 'whatsapp_live': 'NOT VERIFIED',
            'sandbox_available': bool(c.execute('SELECT demo FROM tenants WHERE id=?', (tenant,)).fetchone()[0])}


@router.get('/api/operations')
def operations(user=Depends(current_user)):
    with db.connection() as c:
        return operation_status(c, user['tenant_id'])


@router.post('/api/bridge/status')
def bridge_status(request: Request):
    with db.connection() as c:
        return operation_status(c, bridge_tenant(request, c))


@router.post('/api/bridge/whatsapp/dispatch')
async def whatsapp_delivery(request: Request):
    from .integrations import dispatch
    with db.connection() as c:
        tenant = bridge_tenant(request, c)
    return await dispatch(tenant, channel='whatsapp')


@router.post('/api/bridge/reconcile')
def reconcile(request: Request, background: BackgroundTasks):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = bridge_tenant(request, c)
        from .telegram import configuration
        if configuration().get('enabled'):
            from .integrations import dispatch
            background.add_task(dispatch, tenant, 'telegram')
        # A crashed sender cannot safely assume delivery failed. Escalate, never replay.
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        c.execute("UPDATE outbox SET status='Uncertain',error='Interrupted provider delivery; reconcile before retry' WHERE tenant_id=? AND channel='telegram' AND status='Sending' AND next_attempt<?", (tenant, cutoff))
        created = 0
        for row in c.execute("SELECT id,status FROM outbox WHERE tenant_id=? AND status IN ('Uncertain','Failed')", (tenant,)).fetchall():
            category = 'delivery_reconciliation' if row['status'] == 'Uncertain' else 'provider_rejected'
            identifier = db.uid()
            cursor = c.execute('INSERT OR IGNORE INTO incidents VALUES(?,?,?,?,?,?,?,?)', (identifier, tenant, 'outbox:' + row['id'], '', '', category, 'Open', db.now()))
            created += cursor.rowcount
            if cursor.rowcount:
                db.audit(c, tenant, 'n8n', 'incident.opened', identifier, category)
        return {'incidents_created': created, 'uncertain_deliveries_retried': 0, 'open_incidents': operation_status(c, tenant)['open_incidents']}


class IncidentInput(Model):
    event_id: str = Field(pattern=r'^[a-zA-Z0-9_.:-]{1,200}$')
    workflow_id: str = Field(default='', pattern=r'^[a-zA-Z0-9_-]{0,100}$')
    execution_id: str = Field(default='', pattern=r'^[a-zA-Z0-9_-]{0,100}$')
    category: Literal['workflow_failure', 'delivery_reconciliation', 'provider_rejected'] = 'workflow_failure'


@router.post('/api/bridge/incidents')
def bridge_incident(data: IncidentInput, request: Request):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = bridge_tenant(request, c)
        identifier = db.uid()
        inserted = c.execute('INSERT OR IGNORE INTO incidents VALUES(?,?,?,?,?,?,?,?)', (identifier, tenant, data.event_id, data.workflow_id, data.execution_id, data.category, 'Open', db.now()))
        if inserted.rowcount:
            db.audit(c, tenant, 'n8n', 'incident.opened', identifier, data.category)
        row = c.execute('SELECT id,status FROM incidents WHERE tenant_id=? AND event_id=?', (tenant, data.event_id)).fetchone()
    return {'incident_id': row['id'], 'status': row['status'], 'duplicate': not bool(inserted.rowcount)}


@router.patch('/api/incidents/{incident_id}/resolve')
def resolve_incident(incident_id: str, user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        require(c, 'incidents', user['tenant_id'], incident_id)
        c.execute("UPDATE incidents SET status='Resolved' WHERE tenant_id=? AND id=?", (user['tenant_id'], incident_id))
        db.audit(c, user['tenant_id'], user['id'], 'incident.resolved', incident_id)
    return {'status': 'Resolved'}


class SandboxMessage(Model):
    contact_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    event_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    name: str = Field(default='Sandbox customer', min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=4000)
    consent: bool = False


@router.post('/api/sandbox/whatsapp')
@db.serialized_conversation
async def sandbox_message(data: SandboxMessage, user=Depends(current_user)):
    from .assistant import respond
    admin(user)
    tenant = user['tenant_id']
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute('SELECT demo FROM tenants WHERE id=?', (tenant,)).fetchone()[0]:
            raise HTTPException(403, 'WhatsApp sandbox requires an isolated fictional demo workspace')
        contact = 'sandbox:' + data.contact_id
        lead, created = create_lead(c, tenant, {'name': data.name, 'source': 'whatsapp', 'external_id': contact, 'consent': data.consent}, user['id'])
        event = 'sandbox:' + data.event_id
        inserted = c.execute('INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?)', (db.uid(), tenant, 'whatsapp', event, db.now()))
        if not inserted.rowcount:
            if created:
                raise HTTPException(409, 'Sandbox event belongs to another contact')
            message = c.execute("SELECT lead_id FROM messages WHERE tenant_id=? AND channel='whatsapp' AND external_id=?", (tenant, event)).fetchone()
            if not message or message['lead_id'] != lead['id']:
                raise HTTPException(409, 'Sandbox event belongs to another contact')
            return {'duplicate': True, 'lead_id': lead['id'], 'sandbox': True}
        result = await respond(c, tenant, lead, data.text, 'whatsapp', event, allow_model=False)
        db.audit(c, tenant, user['id'], 'sandbox.whatsapp', lead['id'], 'Provider-free rehearsal; no delivery queued')
        return {'sandbox': True, 'duplicate': False, 'lead_id': lead['id'], 'reply': result['reply'], 'mode': result['mode'],
                'intelligence': lead_intelligence(c, tenant, lead['id']), 'matches': result['matches']}
