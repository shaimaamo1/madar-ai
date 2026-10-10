"""Official channel adapters. Receiving never implies permission to send externally."""
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import Field

from . import db
from .assistant import respond
from .domain import create_lead, require, tick
from .models import LeadInput, Model
from .security import admin, current_user, limit
from .urls import service_url

router = APIRouter()
GRAPH = 'https://graph.facebook.com/v23.0'


def integration_tenant(c):
    tenant = os.getenv('MADAR_INTEGRATION_TENANT_ID', '')
    if not tenant or not c.execute('SELECT 1 FROM tenants WHERE id=?', (tenant,)).fetchone():
        raise HTTPException(503, 'Integration tenant is not configured')
    return tenant


def bearer(request, variable):
    expected = os.getenv(variable)
    provided = request.headers.get('authorization', '').removeprefix('Bearer ')
    if not expected or not secrets.compare_digest(provided, expected):
        raise HTTPException(401, 'Integration authorization required')


async def ingest(c, tenant, channel, event_id, name, contact, text, consent=False):
    from .main import queue_message
    # Event receipt and CRM effects commit atomically, including reply queue.
    cursor = c.execute('INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?)', (db.uid(), tenant, channel, event_id, db.now()))
    if not cursor.rowcount:
        return {'duplicate': True}
    lead, _ = create_lead(c, tenant, {'name': name, 'source': channel, 'external_id': contact, 'consent': consent})
    result = await respond(c, tenant, lead, text, channel, event_id)
    if result['reply']:
        queue_message(c, tenant, lead['id'], channel, result['reply'], 'event:' + channel + ':' + event_id)
    return {'accepted': True}


@router.post('/webhooks/telegram')
@db.serialized_conversation
async def telegram(request: Request):
    expected = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')
    if not expected or not secrets.compare_digest(request.headers.get('x-telegram-bot-api-secret-token', ''), expected):
        raise HTTPException(401, 'Webhook secret required')
    data = await request.json()
    message = data.get('message', {})
    if not message.get('text') or message.get('chat', {}).get('type') != 'private':
        return {'ignored': True}
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = integration_tenant(c)
        return await ingest(c, tenant, 'telegram', str(data['update_id']), message.get('from', {}).get('first_name', 'Telegram visitor'), str(message['chat']['id']), message['text'][:4000])


@router.get('/webhooks/meta')
def meta_challenge(request: Request):
    params = request.query_params
    expected = os.getenv('WHATSAPP_VERIFY_TOKEN', '')
    if not expected or params.get('hub.mode') != 'subscribe' or not secrets.compare_digest(params.get('hub.verify_token', ''), expected):
        raise HTTPException(403, 'Verification failed')
    return PlainTextResponse(params.get('hub.challenge', ''))


@router.post('/webhooks/meta')
@db.serialized_conversation
async def meta(request: Request):
    body = await request.body()
    if len(body) > 1048576:
        raise HTTPException(413, 'Request too large')
    secret = os.getenv('META_APP_SECRET', '')
    expected = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not secret or not secrets.compare_digest(request.headers.get('x-hub-signature-256', ''), expected):
        raise HTTPException(401, 'Invalid Meta signature')
    try:
        data = json.loads(body)
    except ValueError:
        raise HTTPException(400, 'Invalid JSON')
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = integration_tenant(c)
        count = 0
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                if change.get('field') == 'leadgen':
                    key = os.getenv('META_PAGE_ACCESS_TOKEN')
                    if not key:
                        raise HTTPException(503, 'Facebook Lead Ads token missing')
                    lead_id = str(value.get('leadgen_id', ''))
                    async with httpx.AsyncClient(timeout=20) as client:
                        response = await client.get(GRAPH + '/' + lead_id, headers={'Authorization': 'Bearer ' + key}, params={'fields': 'field_data'})
                        if response.status_code != 200:
                            raise HTTPException(502, 'Lead Ads fetch failed')
                        fields = {f['name']: f.get('values', [''])[0] for f in response.json().get('field_data', [])}
                    cursor = c.execute('INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?)', (db.uid(), tenant, 'facebook', lead_id, db.now()))
                    if cursor.rowcount:
                        create_lead(c, tenant, {'name': fields.get('full_name', 'Facebook inquiry'), 'phone': fields.get('phone_number', ''), 'email': fields.get('email', ''), 'source': 'facebook', 'external_id': lead_id, 'consent': False})
                        count += 1
                for message in value.get('messages', []):
                    if message.get('type') == 'text':
                        name = value.get('contacts', [{}])[0].get('profile', {}).get('name', 'WhatsApp visitor')
                        await ingest(c, tenant, 'whatsapp', message['id'], name, message['from'], message['text']['body'][:4000])
                        count += 1
                for status in value.get('statuses', []):
                    state = status.get('status', '').capitalize()
                    if state in ('Sent', 'Delivered', 'Read', 'Failed'):
                        c.execute('UPDATE outbox SET status=? WHERE tenant_id=? AND external_id=?', (state, tenant, status['id']))
            for event in entry.get('messaging', []):
                message = event.get('message', {})
                if message.get('text') and not message.get('is_echo'):
                    channel = 'instagram' if data.get('object') == 'instagram' else 'facebook'
                    await ingest(c, tenant, channel, message['mid'], 'Messaging visitor', str(event['sender']['id']), message['text'][:4000])
                    count += 1
    return {'accepted': count}


class IngestInput(Model):
    event_id: str = Field(min_length=1, max_length=200)
    lead: LeadInput
    text: str = Field(default='', max_length=4000)


@router.post('/api/integrations/ingest')
@db.serialized_conversation
async def integration_ingest(data: IngestInput, request: Request):
    bearer(request, 'MADAR_INGEST_TOKEN')
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = integration_tenant(c)
        cursor = c.execute('INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?)', (db.uid(), tenant, data.lead.source, data.event_id, db.now()))
        if not cursor.rowcount:
            return {'duplicate': True}
        lead, created = create_lead(c, tenant, data.lead.model_dump())
        if data.text:
            result = await respond(c, tenant, lead, data.text, data.lead.source)
            if result['reply'] and data.lead.source != 'website':
                from .main import queue_message
                queue_message(c, tenant, lead['id'], data.lead.source, result['reply'], 'event:' + data.lead.source + ':' + data.event_id)
        return {'lead_id': lead['id'], 'created': created}


@router.post('/api/bridge/tick')
def bridge_tick(request: Request):
    bearer(request, 'MADAR_BRIDGE_TOKEN')
    with db.connection() as c:
        return tick(c, integration_tenant(c))


@router.post('/api/bridge/dispatch')
async def bridge_dispatch(request: Request):
    bearer(request, 'MADAR_BRIDGE_TOKEN')
    with db.connection() as c:
        tenant = integration_tenant(c)
    return await dispatch(tenant)


@router.post('/api/integrations/dispatch')
async def manual_dispatch(user=Depends(current_user)):
    admin(user)
    return await dispatch(user['tenant_id'])


class TemplateInput(Model):
    lead_id: str
    template_name: str = Field(pattern=r'^[a-z0-9_]{1,100}$')
    language: str = Field(pattern=r'^[a-z]{2}(?:_[A-Z]{2})?$')
    parameters: list[str] = Field(default_factory=list, max_length=10)


@router.post('/api/integrations/whatsapp/template')
def template(data: TemplateInput, user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        lead = require(c, 'leads', user['tenant_id'], data.lead_id)
        if lead['source'] != 'whatsapp' or not lead['consent'] or lead['opted_out']:
            raise HTTPException(422, 'Template requires a WhatsApp lead with recorded consent')
        if any(not text.strip() or len(text) > 1000 for text in data.parameters):
            raise HTTPException(422, 'Template text parameters must be nonempty and at most 1000 characters')
        content = {'name': data.template_name, 'language': {'code': data.language}}
        if data.parameters:
            content['components'] = [{'type': 'body', 'parameters': [{'type': 'text', 'text': value} for value in data.parameters]}]
        payload = json.dumps(content)
        c.execute('INSERT INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (db.uid(), user['tenant_id'], data.lead_id, 'whatsapp', '', payload, 'template:' + db.uid(), 'Pending', 0, db.now(), '', '', db.now()))
    return {'queued': True, 'note': 'Provider must approve the template; send approval gate still applies'}


async def dispatch(tenant, channel=None):
    if os.getenv('MADAR_ALLOW_EXTERNAL_SEND') != 'true':
        return {'sent': 0, 'blocked': 'Owner approval required before real external messages'}
    if tenant != os.getenv('MADAR_INTEGRATION_TENANT_ID'):
        raise HTTPException(403, 'Integration tenant mismatch')
    sent, held = 0, 0
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        # Never retry uncertain delivery automatically; operator must reconcile provider state.
        rows = [dict(r) for r in c.execute("SELECT * FROM outbox WHERE tenant_id=? AND status IN ('Pending','Retry') AND next_attempt<=? AND attempts<5 AND (? IS NULL OR channel=?) ORDER BY created_at LIMIT 10", (tenant, db.now(), channel, channel))]
        for row in rows:
            c.execute("UPDATE outbox SET status='Sending',attempts=attempts+1 WHERE id=? AND tenant_id=?", (row['id'], tenant))
    for row in rows:
        with db.connection() as c:
            lead = require(c, 'leads', tenant, row['lead_id'])
            last = c.execute("SELECT MAX(created_at) FROM messages WHERE tenant_id=? AND lead_id=? AND direction='inbound' AND channel=?", (tenant, lead['id'], row['channel'])).fetchone()[0]
        reactive = row['dedupe_key'].startswith(('event:', 'manual:'))
        recent = last and datetime.fromisoformat(last) > datetime.now(timezone.utc) - timedelta(hours=24)
        status, error, external_id = 'Held', '', ''
        if lead['external_id'].startswith('sandbox:'):
            error = 'Sandbox contact cannot receive real provider messages'
        elif lead['opted_out'] or (not reactive and not lead['consent']):
            error = 'Opt-out or no follow-up consent'
        elif row['channel'] in ('whatsapp', 'instagram', 'facebook') and not recent and not row['template']:
            error = 'Outside messaging window; approved template required'
        else:
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    if row['channel'] == 'telegram':
                        token = os.getenv('TELEGRAM_BOT_TOKEN')
                        if not token:
                            raise ValueError('Telegram credentials missing')
                        response = await client.post('https://api.telegram.org/bot' + token + '/sendMessage', json={'chat_id': lead['external_id'], 'text': row['body']})
                    elif row['channel'] == 'whatsapp':
                        token, phone = os.getenv('WHATSAPP_ACCESS_TOKEN'), os.getenv('WHATSAPP_PHONE_NUMBER_ID')
                        if not token or not phone:
                            raise ValueError('WhatsApp credentials missing')
                        payload = {'messaging_product': 'whatsapp', 'to': lead['external_id'] or lead['phone'], 'type': 'template' if row['template'] else 'text'}
                        payload['template' if row['template'] else 'text'] = json.loads(row['template']) if row['template'] else {'body': row['body']}
                        response = await client.post(GRAPH + '/' + phone + '/messages', headers={'Authorization': 'Bearer ' + token}, json=payload)
                    elif row['channel'] in ('facebook', 'instagram'):
                        token = os.getenv('META_PAGE_ACCESS_TOKEN')
                        if not token:
                            raise ValueError('Meta page credentials missing')
                        response = await client.post(GRAPH + '/me/messages', headers={'Authorization': 'Bearer ' + token}, json={'recipient': {'id': lead['external_id']}, 'message': {'text': row['body']}})
                    else:
                        raise ValueError('No delivery provider configured for this channel')
                if response.status_code == 429 or response.status_code >= 500:
                    status, error = ('Failed', 'Provider retry limit reached') if row['attempts'] + 1 >= 5 else ('Retry', 'Provider temporarily unavailable')
                elif response.status_code >= 400:
                    status, error = 'Failed', f'Provider rejected request (HTTP {response.status_code})'
                else:
                    result = response.json()
                    if row['channel'] == 'telegram' and not result.get('ok'):
                        status, error = 'Failed', 'Telegram rejected request'
                    else:
                        external_id = str(result.get('result', {}).get('message_id', result.get('messages', [{}])[0].get('id', result.get('message_id', ''))))
                        status = 'Sent'
                        sent += 1
            except ValueError as e:
                error = str(e) if 'credentials' in str(e) or 'provider' in str(e) else 'Invalid provider response'
            except httpx.HTTPError:
                status, error = 'Uncertain', 'Connection failed during delivery; reconcile before retry'
        if status == 'Held':
            held += 1
        with db.connection() as c:
            retry = (datetime.now(timezone.utc) + timedelta(minutes=2 ** (row['attempts'] + 1))).isoformat()
            c.execute('UPDATE outbox SET status=?,error=?,external_id=?,next_attempt=? WHERE tenant_id=? AND id=?', (status, error, external_id, retry, tenant, row['id']))
            db.audit(c, tenant, 'dispatcher', 'outbox.' + status.lower(), row['id'], error)
    return {'sent': sent, 'held': held}


@router.post('/api/integrations/{name}/verify')
async def verify(name: str, user=Depends(current_user)):
    admin(user)
    if name != 'language_model' and user['tenant_id'] != os.getenv('MADAR_INTEGRATION_TENANT_ID'):
        raise HTTPException(422, 'Bind this tenant before verifying the integration')
    headers = {}
    if name == 'n8n':
        if os.getenv('N8N_ENABLED', 'false') != 'true':
            raise HTTPException(422, 'Local n8n integration is disabled; configure it on your local machine')
        base = os.getenv('N8N_BASE_URL', '')
        try:
            base = service_url(base, 'n8n')
        except ValueError as e:
            raise HTTPException(422, str(e))
        url = base.rstrip('/') + '/api/v1/workflows?limit=1'
        headers = {'X-N8N-API-KEY': os.getenv('N8N_API_KEY', '')}
    elif name == 'telegram':
        url = 'https://api.telegram.org/bot' + os.getenv('TELEGRAM_BOT_TOKEN', '') + '/getMe'
    elif name == 'whatsapp':
        url = GRAPH + '/' + os.getenv('WHATSAPP_PHONE_NUMBER_ID', '') + '?fields=id,display_phone_number'
        headers = {'Authorization': 'Bearer ' + os.getenv('WHATSAPP_ACCESS_TOKEN', '')}
    elif name == 'language_model':
        url = 'https://api.openai.com/v1/models'
        headers = {'Authorization': 'Bearer ' + os.getenv('MADAR_AI_API_KEY', '')}
    else:
        raise HTTPException(422, 'No read-only verification implemented for this channel')
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=headers)
        verified = response.status_code == 200 and (name != 'telegram' or response.json().get('ok') is True)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'Provider unreachable; no credentials logged')
    with db.connection() as c:
        db.audit(c, user['tenant_id'], user['id'], 'integration.verify', name, 'Verified' if verified else f'HTTP {response.status_code}')
    return {'verified': verified, 'http_status': response.status_code}
