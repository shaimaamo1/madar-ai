from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request

from . import db
from .domain import book, require
from .domain import create_lead
from .models import LeadInput, Model
from .security import digest, limit

router = APIRouter()


@router.get('/api/public/company/{slug}')
def public_company(slug: str):
    with db.connection() as c:
        row = c.execute('SELECT id,demo FROM tenants WHERE slug=?', (slug,)).fetchone()
        if not row:
            raise HTTPException(404, 'Company not found')
        cfg = db.settings(c, row['id'])
    return {k: cfg[k] for k in ('company_name', 'brand_color', 'logo_url', 'currency', 'assistant_name', 'language', 'timezone')} | {'demo': bool(row['demo'])}


def chat_identity(c, slug, session):
    row = c.execute('SELECT t.id AS tenant_id,s.lead_id FROM tenants t JOIN chat_sessions s ON s.tenant_id=t.id WHERE t.slug=? AND s.token_hash=?', (slug, digest(session))).fetchone()
    if not row:
        raise HTTPException(401, 'Start a chat before booking')
    return row['tenant_id'], row['lead_id']


class SlotRequest(Model):
    tenant_slug: str
    session: str
    property_id: str


class PublicBooking(SlotRequest):
    start_at: str


class ChatHistory(Model):
    tenant_slug: str
    session: str


class WebsiteForm(Model):
    tenant_slug: str
    lead: LeadInput


@router.post('/api/public/lead')
def website_form(data: WebsiteForm, request: Request):
    limit('form:' + request.client.host, 10, 60)
    if data.lead.source != 'website' or data.lead.external_id:
        raise HTTPException(422, 'Website form source must be website')
    with db.connection() as c:
        tenant = c.execute('SELECT id FROM tenants WHERE slug=?', (data.tenant_slug,)).fetchone()
        if not tenant:
            raise HTTPException(404, 'Company not found')
        c.execute('BEGIN IMMEDIATE')
        # Deduplication must not let a caller take over an existing contact's chat.
        create_lead(c, tenant[0], data.lead.model_dump())
    # Same public response regardless of existing contact; no CRM ID or history access.
    return {'received': True}


@router.post('/api/public/history')
def public_history(data: ChatHistory, request: Request):
    limit('history:' + request.client.host, 60, 60)
    with db.connection() as c:
        tenant, lead = chat_identity(c, data.tenant_slug, data.session)
        rows = c.execute('SELECT direction,body,created_at FROM messages WHERE tenant_id=? AND lead_id=? ORDER BY created_at DESC LIMIT 100', (tenant, lead)).fetchall()
    return {'messages': [dict(r) for r in reversed(rows)]}


@router.post('/api/public/slots')
def available_slots(data: SlotRequest, request: Request):
    limit('slots:' + request.client.host, 30, 60)
    with db.connection() as c:
        tenant, lead_id = chat_identity(c, data.tenant_slug, data.session)
        result = inventory_slots(c, tenant, lead_id, data.property_id)
        return {**result, 'slots': [{k:v for k,v in slot.items() if k != 'agent_id'} for slot in result['slots']]}


def inventory_slots(c, tenant, lead_id, property_id):
    p = require(c, 'properties', tenant, property_id)
    if p['status'] != 'Available':
        return {'slots': []}
    cfg = db.settings(c, tenant)
    zone = ZoneInfo(cfg['timezone'])
    current = datetime.now(timezone.utc)
    agents = c.execute('SELECT id FROM users WHERE tenant_id=? AND active=1 ORDER BY id', (tenant,)).fetchall()
    slots = []
    for day in range(1, 8):
        base = (current.astimezone(zone) + timedelta(days=day)).replace(minute=0, second=0, microsecond=0)
        for hour in range(cfg['business_start'], cfg['business_end']):
            start = base.replace(hour=hour).astimezone(timezone.utc)
            end = start + timedelta(hours=1)
            a, b = start.isoformat(), end.isoformat()
            for agent in agents:
                conflict = c.execute("SELECT 1 FROM appointments WHERE tenant_id=? AND status='Booked' AND (agent_id=? OR lead_id=? OR property_id=?) AND start_at<? AND end_at>?", (tenant, agent['id'], lead_id, p['id'], b, a)).fetchone()
                if not conflict:
                    slots.append({'start_at': a, 'end_at': b, 'agent_id': agent['id']})
                    break
            if len(slots) >= 15:
                return {'slots': slots, 'timezone': cfg['timezone']}
    return {'slots': slots, 'timezone': cfg['timezone']}


@router.post('/api/public/book')
def public_book(data: PublicBooking, request: Request):
    limit('book:' + request.client.host, 10, 60)
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant, lead = chat_identity(c, data.tenant_slug, data.session)
        agents = c.execute('SELECT id FROM users WHERE tenant_id=? AND active=1 ORDER BY id', (tenant,)).fetchall()
        for agent in agents:
            try:
                appointment = book(c, tenant, {'lead_id': lead, 'property_id': data.property_id, 'agent_id': agent['id'], 'start_at': data.start_at}, 'website-customer')
                return {'booked': True, 'start_at': appointment['start_at'], 'end_at': appointment['end_at']}
            except HTTPException as e:
                if e.status_code != 409:
                    raise
        raise HTTPException(409, 'This time is no longer available')
