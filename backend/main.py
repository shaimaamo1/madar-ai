import json
import mimetypes
import asyncio
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from argon2.exceptions import VerificationError
from pydantic import StrictBool
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import db, sample_data
from .assistant import respond
from .domain import book, create_lead, insights, match_properties, record, require, score, tick
from .models import Model, Booking, Chat, DealInput, LeadInput, LeadPatch, Login, PasswordInput, PropertyInput, PublicChat, SettingsInput, TaskInput, UserInput, WorkspaceInput
from .security import DEMO, admin, bootstrap, check_origin, current_user, demo_workspace, digest, hasher, limit, login_session


@asynccontextmanager
async def lifespan(app):
    db.migrate()
    bootstrap()
    if not os.getenv('MADAR_INTEGRATION_TENANT_ID') and os.getenv('MADAR_INTEGRATION_WORKSPACE'):
        with db.connection() as c:
            tenant = c.execute('SELECT id FROM tenants WHERE slug=?', (os.environ['MADAR_INTEGRATION_WORKSPACE'],)).fetchone()
        if not tenant:
            raise RuntimeError('Configured integration workspace does not exist')
        os.environ['MADAR_INTEGRATION_TENANT_ID'] = tenant[0]
    from .telegram_polling import worker
    task = asyncio.create_task(worker()) if os.getenv('MADAR_TELEGRAM_POLL_WORKER', 'true') == 'true' else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title='MADAR AI', version='1.1.0', lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get('/api/docs', include_in_schema=False)
def api_contract():
    return app.openapi()


@app.middleware('http')
async def guards(request, call_next):
    try:
        check_origin(request)
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > 1048576:
            return JSONResponse({'detail': 'Request too large'}, status_code=413)
        response = await call_next(request)
    except HTTPException as e:
        response = JSONResponse({'detail': e.detail}, status_code=e.status_code)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; connect-src 'self'; script-src 'self'; frame-ancestors 'self'"
    if request.url.path == '/chat':
        del response.headers['X-Frame-Options']
        response.headers['Content-Security-Policy'] = response.headers['Content-Security-Policy'].replace("frame-ancestors 'self'", 'frame-ancestors https:')
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(RequestValidationError)
async def safe_validation(request, error):
    if request.url.path.startswith('/api/telegram/'):
        return JSONResponse({'detail': 'Invalid Telegram configuration; input values omitted'}, status_code=422)
    return await request_validation_exception_handler(request, error)


@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error(request, exception):
    return JSONResponse({'detail': 'A record conflicts with existing data'}, status_code=409)


@app.get('/api/health')
def health():
    with db.connection() as c:
        c.execute('SELECT 1').fetchone()
    return {'status': 'ok', 'service': 'madar-ai'}


@app.get('/api/public/runtime')
def public_runtime():
    return {'demo_enabled': DEMO}


@app.post('/api/auth/login')
def login(data: Login, request: Request, response: Response):
    limit('login:' + request.client.host, 10, 300)
    with db.connection() as c:
        user = c.execute("SELECT u.* FROM users u JOIN tenants t ON t.id=u.tenant_id WHERE t.slug=? AND u.email=? AND u.active=1 AND NOT EXISTS (SELECT 1 FROM sample_records sr WHERE sr.tenant_id=u.tenant_id AND sr.table_name='users' AND sr.record_id=u.id)", (data.workspace, data.email.lower())).fetchone()
        try:
            valid = user and hasher.verify(user['password_hash'], data.password)
        except VerificationError:
            valid = False
        if not valid:
            raise HTTPException(401, 'Invalid workspace or credentials')
        login_session(c, user['id'], response)
        db.audit(c, user['tenant_id'], user['id'], 'auth.login', user['id'])
    return {'ok': True}


@app.post('/api/auth/demo')
def demo(request: Request, response: Response):
    limit('demo:' + request.client.host, 10, 300)
    with db.connection() as c:
        return demo_workspace(c, response)


@app.post('/api/auth/logout')
def logout(request: Request, response: Response):
    with db.connection() as c:
        c.execute('DELETE FROM sessions WHERE token_hash=?', (digest(request.cookies.get('madar_session', '')),))
    response.delete_cookie('madar_session')
    return {'ok': True}


@app.post('/api/auth/password')
def password_change(data: PasswordInput, request: Request, response: Response, user=Depends(current_user)):
    limit('password:' + user['id'], 5, 300)
    try:
        hasher.verify(user['password_hash'], data.current_password)
    except VerificationError:
        raise HTTPException(401, 'Current password is incorrect')
    with db.connection() as c:
        c.execute('UPDATE users SET password_hash=? WHERE id=? AND tenant_id=?', (hasher.hash(data.new_password), user['id'], user['tenant_id']))
        c.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
        login_session(c, user['id'], response)
        db.audit(c, user['tenant_id'], user['id'], 'auth.password_changed', user['id'])
    return {'ok': True}


@app.post('/api/workspaces')
def create_workspace(data: WorkspaceInput, user=Depends(current_user)):
    admin(user)
    if data.slug.startswith('demo-'):
        raise HTTPException(422, 'Demo workspace prefix is reserved')
    with db.connection() as c:
        if c.execute('SELECT COUNT(*) FROM tenants WHERE demo=0').fetchone()[0] >= 100:
            raise HTTPException(409, 'Workspace limit reached')
        tenant, owner = db.uid(), db.uid()
        c.execute('INSERT INTO tenants VALUES(?,?,?,?,?)', (tenant, data.slug, data.company_name, json.dumps(db.default_settings(data.company_name)), 0))
        c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)', (owner, tenant, data.owner_email.lower(), data.owner_name, 'admin', hasher.hash(data.owner_password), 1))
        db.audit(c, tenant, owner, 'workspace.created', tenant)
        db.audit(c, user['tenant_id'], user['id'], 'workspace.provisioned', tenant, data.slug)
    return {'workspace': data.slug, 'tenant_id': tenant}


@app.get('/api/state')
def state(user=Depends(current_user)):
    tenant = user['tenant_id']
    with db.connection() as c:
        company = dict(c.execute('SELECT * FROM tenants WHERE id=?', (tenant,)).fetchone())
        company['settings'] = json.loads(company['settings'])
        result = {'company': company, 'user': {k: user[k] for k in ('id', 'name', 'email', 'role')}, 'insights': insights(c, tenant)}
        for table in ('leads', 'properties', 'messages', 'appointments', 'tasks', 'deals', 'activities', 'outbox', 'incidents', 'consent_events'):
            result[table] = [record(r) for r in c.execute(f'SELECT * FROM {table} WHERE tenant_id=? ORDER BY created_at DESC LIMIT 1000', (tenant,))]
        result['sample_data'] = sample_data.status(c, tenant)
        result['users'] = [record(r) for r in c.execute('SELECT id,name,email,role,active FROM users WHERE tenant_id=?', (tenant,))]
        result['conversation_controls'] = [dict(r) for r in c.execute('SELECT * FROM conversation_controls WHERE tenant_id=?', (tenant,))]
    result['integrations'] = integration_status(tenant)
    return result


def integration_status(tenant):
    bound = tenant == os.getenv('MADAR_INTEGRATION_TENANT_ID')
    specs = {'n8n': ('N8N_BASE_URL', 'N8N_API_KEY', 'MADAR_BRIDGE_TOKEN'), 'telegram': ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_WEBHOOK_SECRET'),
             'whatsapp': ('WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_PHONE_NUMBER_ID', 'META_APP_SECRET', 'WHATSAPP_VERIFY_TOKEN'),
             'facebook': ('META_PAGE_ACCESS_TOKEN', 'META_APP_SECRET'), 'instagram': ('META_PAGE_ACCESS_TOKEN', 'META_APP_SECRET'),
             'email': ('MADAR_INGEST_TOKEN',), 'crm': ('MADAR_INGEST_TOKEN',), 'language_model': ('MADAR_AI_API_KEY',)}
    result = [{'name': 'website', 'status': 'Operational', 'detail': 'Shared CRM and sales assistant; no external credentials'}]
    for name, keys in specs.items():
        if name == 'n8n' and os.getenv('N8N_ENABLED', 'false') != 'true':
            result.append({'name': name, 'status': 'Local setup required', 'missing': ['N8N_ENABLED', *keys], 'detail': 'Self-hosted n8n runs on your computer; Cloud preview does not connect to it'})
            continue
        if name == 'telegram':
            from .telegram import configuration, status
            cfg = status(configuration()) if bound else {}
            result.append({'name': name, 'status': 'Operational' if cfg.get('verified') else 'Configured, unverified' if cfg.get('configured') else 'Needs authorization',
                           'missing': [] if cfg.get('configured') else list(keys), 'detail': 'Telegram delivery enabled by operator' if cfg.get('enabled') else 'Telegram delivery disabled'})
            continue
        configured = all(os.getenv(k) for k in keys) and (bound or name == 'language_model')
        result.append({'name': name, 'status': 'Configured, unverified' if configured else 'Needs authorization', 'missing': [k for k in keys if not os.getenv(k)] + ([] if bound or name == 'language_model' else ['MADAR_INTEGRATION_TENANT_ID']), 'detail': 'External delivery disabled' if os.getenv('MADAR_ALLOW_EXTERNAL_SEND') != 'true' else 'Delivery enabled by operator'})
    return result


@app.post('/api/leads')
def add_lead(data: LeadInput, user=Depends(current_user)):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        lead, created = create_lead(c, user['tenant_id'], data.model_dump(), user['id'])
    return {'lead': lead, 'created': created}


@app.patch('/api/leads/{lead_id}')
def edit_lead(lead_id: str, data: LeadPatch, user=Depends(current_user)):
    tenant = user['tenant_id']
    with db.connection() as c:
        lead = require(c, 'leads', tenant, lead_id)
        patch = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        if patch.get('stage') and patch['stage'] not in db.settings(c, tenant)['stages']:
            raise HTTPException(422, 'Unknown pipeline stage')
        if patch.get('assigned_to'):
            assigned = require(c, 'users', tenant, patch['assigned_to'])
            if assigned.get('sample') or not assigned['active']:
                raise HTTPException(409, 'Choose an active agent')
        if patch.get('opted_out'):
            patch['consent'] = False
        if patch.get('consent') and lead['opted_out'] and patch.get('opted_out') is not False:
            raise HTTPException(422, 'Explicitly clear opt-out before recording new consent')
        if 'consent' in patch or 'opted_out' in patch:
            c.execute('INSERT INTO consent_events VALUES(?,?,?,?,?,?,?)', (db.uid(), tenant, lead_id, int(patch.get('consent', lead['consent'])), user['id'], 'Operator recorded customer permission', db.now()))
        lead.update(patch)
        patch['score'] = score(lead)
        patch['updated_at'] = db.now()
        c.execute(f"UPDATE leads SET {','.join(k+'=?' for k in patch)} WHERE tenant_id=? AND id=?", [*patch.values(), tenant, lead_id])
        db.audit(c, tenant, user['id'], 'lead.updated', lead_id, ','.join(patch))
    return {'ok': True}


@app.get('/api/leads/{lead_id}/matches')
def matches(lead_id: str, user=Depends(current_user)):
    with db.connection() as c:
        return match_properties(c, user['tenant_id'], require(c, 'leads', user['tenant_id'], lead_id))


@app.post('/api/leads/{lead_id}/chat')
@db.serialized_conversation
async def sales_chat(lead_id: str, data: Chat, user=Depends(current_user)):
    with db.connection() as c:
        lead = require(c, 'leads', user['tenant_id'], lead_id)
        return await respond(c, user['tenant_id'], lead, data.text)


@app.post('/api/leads/{lead_id}/reply')
def human_reply(lead_id: str, data: Chat, user=Depends(current_user)):
    with db.connection() as c:
        lead = require(c, 'leads', user['tenant_id'], lead_id)
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)', (db.uid(), user['tenant_id'], lead_id, 'outbound', lead['source'], data.text, '', db.now()))
        if lead['source'] != 'website':
            queue_message(c, user['tenant_id'], lead_id, lead['source'], data.text, 'manual:' + db.uid())
        db.audit(c, user['tenant_id'], user['id'], 'message.human', lead_id)
    return {'ok': True, 'external_delivery': 'sample inbox only; external delivery blocked' if lead.get('sample') else 'queued, approval gate applies' if lead['source'] != 'website' else 'website inbox'}


def queue_message(c, tenant, lead, channel, body, dedupe):
    if sample_data.is_sample(c, tenant, 'leads', lead):
        return
    c.execute('INSERT OR IGNORE INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (db.uid(), tenant, lead, channel, body, '', dedupe, 'Pending', 0, db.now(), '', '', db.now()))


@app.post('/api/public/chat')
@db.serialized_conversation
async def website_chat(data: PublicChat, request: Request):
    limit('chat:' + request.client.host, 30, 60)
    with db.connection() as c:
        tenant = c.execute('SELECT id FROM tenants WHERE slug=?', (data.tenant_slug,)).fetchone()
        if not tenant:
            raise HTTPException(404, 'Company not found')
        tenant = tenant[0]
        if data.session:
            session = c.execute('SELECT lead_id FROM chat_sessions WHERE tenant_id=? AND token_hash=?', (tenant, digest(data.session))).fetchone()
            if not session:
                raise HTTPException(401, 'Invalid chat session')
            lead = require(c, 'leads', tenant, session[0])
            token = data.session
        else:
            lead, _ = create_lead(c, tenant, {'name': data.name, 'source': 'website', 'consent': data.consent})
            token = secrets.token_urlsafe(32)
            c.execute('INSERT INTO chat_sessions VALUES(?,?,?,?)', (digest(token), tenant, lead['id'], db.now()))
        result = await respond(c, tenant, lead, data.text)
    # Public users receive no CRM identity, agent or contact details.
    return {'session': token, 'reply': result['reply'], 'matches': result['matches'], 'mode': result['mode']}


@app.post('/api/properties')
def add_property(data: PropertyInput, user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        values = dict(id=db.uid(), tenant_id=user['tenant_id'], **data.model_dump(), created_at=db.now())
        values['amenities'] = json.dumps(values['amenities'])
        c.execute(f"INSERT INTO properties ({','.join(values)}) VALUES ({','.join('?' for _ in values)})", list(values.values()))
        db.audit(c, user['tenant_id'], user['id'], 'property.created', values['id'])
        availability_tasks(c, user['tenant_id'], values['id'])
    return {'id': values['id']}


@app.patch('/api/properties/{property_id}')
def edit_property(property_id: str, data: PropertyInput, user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        previous = require(c, 'properties', user['tenant_id'], property_id)
        values = data.model_dump()
        values['amenities'] = json.dumps(values['amenities'])
        c.execute(f"UPDATE properties SET {','.join(k+'=?' for k in values)} WHERE tenant_id=? AND id=?", [*values.values(), user['tenant_id'], property_id])
        db.audit(c, user['tenant_id'], user['id'], 'property.updated', property_id)
        if previous['status'] != 'Available' and data.status == 'Available':
            availability_tasks(c, user['tenant_id'], property_id)
    return {'ok': True}


def availability_tasks(c, tenant, property_id):
    for row in c.execute("SELECT * FROM leads WHERE tenant_id=? AND consent=1 AND opted_out=0 AND stage NOT IN ('Won','Lost')", (tenant,)).fetchall():
        if sample_data.is_sample(c, tenant, 'leads', row['id']):
            continue
        if any(p['id'] == property_id for p in match_properties(c, tenant, record(row))):
            c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)', (db.uid(), tenant, row['id'], 'Matching property now available', db.now(), 'Pending', 'availability', db.now()))


@app.post('/api/appointments')
def add_appointment(data: Booking, user=Depends(current_user)):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        return book(c, user['tenant_id'], data.model_dump(), user['id'])


@app.put('/api/appointments/{appointment_id}')
def reschedule(appointment_id: str, data: Booking, user=Depends(current_user)):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        original = require(c, 'appointments', user['tenant_id'], appointment_id)
        if original['lead_id'] != data.lead_id:
            raise HTTPException(422, 'Rescheduling cannot change customer')
        return book(c, user['tenant_id'], dict(data.model_dump(), id=appointment_id), user['id'])


@app.patch('/api/appointments/{appointment_id}/{status}')
def appointment_status(appointment_id: str, status: str, user=Depends(current_user)):
    if status not in ('Cancelled', 'Completed'):
        raise HTTPException(422, 'Unknown appointment status')
    with db.connection() as c:
        a = require(c, 'appointments', user['tenant_id'], appointment_id)
        if a['status'] == status:
            return {'ok': True}
        if a['status'] != 'Booked':
            raise HTTPException(409, 'This appointment is already closed')
        c.execute('UPDATE appointments SET status=? WHERE tenant_id=? AND id=?', (status, user['tenant_id'], appointment_id))
        if status == 'Completed' and a['status'] != 'Completed':
            c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)', (db.uid(), user['tenant_id'], a['lead_id'], 'Post-viewing feedback', db.now(), 'Pending', 'post-viewing', db.now()))
        db.audit(c, user['tenant_id'], user['id'], 'appointment.' + status.lower(), appointment_id)
    return {'ok': True}


@app.post('/api/tasks')
def add_task(data: TaskInput, user=Depends(current_user)):
    due = normalized_time(data.due_at)
    with db.connection() as c:
        require(c, 'leads', user['tenant_id'], data.lead_id)
        c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)', (db.uid(), user['tenant_id'], data.lead_id, data.title, due, 'Pending', 'followup', db.now()))
    return {'ok': True}


def normalized_time(value):
    try:
        time = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if time.tzinfo is None:
            raise ValueError()
        return time.astimezone(timezone.utc).isoformat()
    except ValueError:
        raise HTTPException(422, 'Use an ISO time with timezone')


@app.patch('/api/tasks/{task_id}/complete')
def complete_task(task_id: str, user=Depends(current_user)):
    with db.connection() as c:
        require(c, 'tasks', user['tenant_id'], task_id)
        c.execute("UPDATE tasks SET status='Completed' WHERE tenant_id=? AND id=?", (user['tenant_id'], task_id))
    return {'ok': True}


@app.post('/api/deals')
def add_deal(data: DealInput, user=Depends(current_user)):
    if data.status == 'Lost' and not data.lost_reason:
        raise HTTPException(422, 'Record a reason for the lost deal')
    with db.connection() as c:
        require(c, 'leads', user['tenant_id'], data.lead_id)
        if data.property_id:
            require(c, 'properties', user['tenant_id'], data.property_id)
        c.execute('INSERT INTO deals VALUES(?,?,?,?,?,?,?,?,?)', (db.uid(), user['tenant_id'], data.lead_id, data.property_id, data.amount, data.commission, data.status, data.lost_reason, db.now()))
        if data.status in ('Won', 'Lost'):
            c.execute('UPDATE leads SET stage=?,updated_at=? WHERE tenant_id=? AND id=?', (data.status, db.now(), user['tenant_id'], data.lead_id))
        db.audit(c, user['tenant_id'], user['id'], 'deal.recorded', data.lead_id, data.status)
    return {'ok': True}


@app.get('/api/analytics')
def analytics(user=Depends(current_user)):
    with db.connection() as c:
        tenant = user['tenant_id']
        leads = [dict(r) for r in c.execute('SELECT * FROM leads WHERE tenant_id=?', (tenant,))]
        deals = [dict(r) for r in c.execute('SELECT * FROM deals WHERE tenant_id=?', (tenant,))]
        appointments = [dict(r) for r in c.execute('SELECT * FROM appointments WHERE tenant_id=?', (tenant,))]
        sample_counts = sample_data.status(c, tenant)['counts']
        sample_ids = sample_data.owned(c, tenant)
        real_lead_ids = {l['id'] for l in leads if l['id'] not in sample_ids['leads']}
        leads = [l for l in leads if l['id'] in real_lead_ids]
        deals = [d for d in deals if d['lead_id'] in real_lead_ids and d['property_id'] not in sample_ids['properties']]
        appointments = [a for a in appointments if a['lead_id'] in real_lead_ids and a['id'] not in sample_ids['appointments']]
        responses = c.execute("SELECT i.lead_id,i.created_at AS received, MIN(o.created_at) AS replied FROM messages i JOIN messages o ON o.tenant_id=i.tenant_id AND o.lead_id=i.lead_id AND o.direction='outbound' AND o.created_at>=i.created_at WHERE i.tenant_id=? AND i.direction='inbound' GROUP BY i.id", (tenant,)).fetchall()
        times = [(datetime.fromisoformat(r['replied']) - datetime.fromisoformat(r['received'])).total_seconds() for r in responses if r['lead_id'] in real_lead_ids]
        sources = {source: sum(l['source'] == source for l in leads) for source in set(l['source'] for l in leads)}
        agents = [{'name': r['name'], 'leads': sum(l['assigned_to'] == r['id'] for l in leads), 'won': sum(l['assigned_to'] == r['id'] and l['stage'] == 'Won' for l in leads), 'appointments':sum(a['agent_id']==r['id'] for a in appointments)} for r in c.execute('SELECT id,name FROM users WHERE tenant_id=?', (tenant,)) if r['id'] not in sample_ids['users']]
        tasks = [dict(r) for r in c.execute('SELECT * FROM tasks WHERE tenant_id=?', (tenant,)) if r['lead_id'] in real_lead_ids and r['id'] not in sample_ids['tasks']]
        demand = {location:sum(l['location']==location for l in leads) for location in sorted({l['location'] for l in leads if l['location']})}
        appointment_activity = {status:sum(a['status']==status for a in appointments) for status in ('Booked','Completed','Cancelled')}
        demo_scope = bool(c.execute('SELECT demo FROM tenants WHERE id=?', (tenant,)).fetchone()[0])
        return {'sample_counts':sample_counts, 'excludes_sample_activity':True, 'demo':demo_scope, 'demand_by_area':demand, 'appointment_activity':appointment_activity, 'followups':{'total':len(tasks),'completed':sum(t['status']=='Completed' for t in tasks),'pending':sum(t['status']=='Pending' for t in tasks)}, 'total_leads': len(leads), 'qualified': sum(l['score'] >= 65 for l in leads), 'conversion_rate': round(100 * sum(l['stage'] == 'Won' for l in leads) / max(len(leads), 1), 1), 'revenue': sum(d['commission'] for d in deals if d['status'] == 'Won'), 'sales_volume': sum(d['amount'] for d in deals if d['status'] == 'Won'), 'open_pipeline': sum(d['amount'] for d in deals if d['status'] == 'Open'), 'appointments': len(appointments), 'appointment_conversion': round(100 * sum(a['status'] == 'Completed' for a in appointments) / max(len(appointments), 1), 1), 'average_response_seconds': round(sum(times)/len(times), 1) if times else None, 'sources': sources, 'agents': agents, 'pipeline': {s: sum(l['stage'] == s for l in leads) for s in db.settings(c, tenant)['stages']}, 'missed_opportunities': sum(i['type'] == 'Leakage' for i in insights(c, tenant))}


@app.put('/api/settings')
def save_settings(data: SettingsInput, user=Depends(current_user)):
    admin(user)
    if data.business_end <= data.business_start:
        raise HTTPException(422, 'Business end must follow business start')
    with db.connection() as c:
        c.execute('UPDATE tenants SET name=?,settings=? WHERE id=?', (data.company_name, json.dumps(data.model_dump()), user['tenant_id']))
        db.audit(c, user['tenant_id'], user['id'], 'settings.updated', user['tenant_id'])
    return {'ok': True}


@app.post('/api/users')
def add_user(data: UserInput, user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        new_id = db.uid()
        c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)', (new_id, user['tenant_id'], data.email.lower(), data.name, data.role, hasher.hash(data.password), 1))
        db.audit(c, user['tenant_id'], user['id'], 'user.created', new_id)
    return {'id': new_id}


@app.patch('/api/users/{user_id}/deactivate')
def deactivate(user_id: str, user=Depends(current_user)):
    admin(user)
    if user_id == user['id']:
        raise HTTPException(422, 'Cannot deactivate your own account')
    with db.connection() as c:
        require(c, 'users', user['tenant_id'], user_id)
        c.execute('UPDATE users SET active=0 WHERE tenant_id=? AND id=?', (user['tenant_id'], user_id))
        c.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
        db.audit(c, user['tenant_id'], user['id'], 'user.deactivated', user_id)
    return {'ok': True}


class SampleConfirmation(Model):
    confirmed: StrictBool = False


def confirm_sample(data):
    if not data.confirmed:
        raise HTTPException(422, 'Explicit sample data confirmation required')


@app.get('/api/sample-data')
def sample_status(user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        sample_data.require_real(c, user['tenant_id'])
        return sample_data.status(c, user['tenant_id'])


@app.post('/api/sample-data/load')
def load_sample(data: SampleConfirmation, user=Depends(current_user)):
    admin(user)
    confirm_sample(data)
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        return sample_data.load(c, user['tenant_id'], user['id'])


@app.post('/api/sample-data/remove')
def remove_sample(data: SampleConfirmation, user=Depends(current_user)):
    admin(user)
    confirm_sample(data)
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        return sample_data.remove(c, user['tenant_id'], user['id'])


@app.post('/api/demo/load')
def load_demo(user=Depends(current_user)):
    admin(user)
    from .seed import seed_demo
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        seed_demo(c, user['tenant_id'], user['id'], hasher.hash(secrets.token_urlsafe(32)))
    return {'ok': True}


@app.post('/api/demo/reset')
def reset_demo(user=Depends(current_user)):
    admin(user)
    from .seed import reset_generated, seed_demo
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        retained = reset_generated(c, user['tenant_id'])
        seed_demo(c, user['tenant_id'], user['id'], hasher.hash(secrets.token_urlsafe(32)))
    return {'ok': True, 'retained_referenced_demo_records': retained}


@app.post('/api/automation/tick')
def automation(user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        return tick(c, user['tenant_id'])


@app.post('/api/copilot/marketing/{property_id}')
def marketing(property_id: str, user=Depends(current_user)):
    with db.connection() as c:
        p = require(c, 'properties', user['tenant_id'], property_id)
        cfg = db.settings(c, user['tenant_id'])
    return {'draft': f"Discover {p['title']} in {p['location']}. {p['size']:g} m², {p['bedrooms']} bedrooms. Listed at {p['price']:,.0f} {cfg['currency']}. Features: {', '.join(p['amenities'])}. Contact {cfg['company_name']} to ask about current availability.\n\nاكتشف {p['title']} في {p['location']}. المساحة {p['size']:g} متر مربع. السعر المسجل {p['price']:,.0f} {cfg['currency']}. تواصل معنا للاستفسار عن التوفر الحالي.", 'published': False, 'mode': 'verified-data template'}


@app.get('/api/report')
def report(user=Depends(current_user)):
    data = analytics(user)
    return {'generated_at': db.now(), 'metrics': data, 'summary': f"{data['total_leads']} leads, {data['qualified']} qualified, {data['missed_opportunities']} need attention. Recorded commission revenue: {data['revenue']:,.0f}. No forecast revenue is treated as earned.", 'method': 'Computed from recorded CRM data'}


# Integration routes registered after core functions to avoid circular imports.
from .telegram import router as telegram_router
app.include_router(telegram_router)

from .integrations import router
app.include_router(router)
from .availability import router as availability_router
app.include_router(availability_router)
from .operations import router as operations_router
app.include_router(operations_router)
from .enterprise import router as enterprise_router
app.include_router(enterprise_router)
from .ai_agents import router as ai_agents_router
app.include_router(ai_agents_router)

# Slim Python images may lack /etc/mime.types entries for WebP.
mimetypes.add_type('image/webp', '.webp')
DEMO_ASSETS = Path(__file__).resolve().parent / 'demo_assets'


@app.get('/demo-assets/property-{number}.svg', include_in_schema=False)
def legacy_demo_photo(number: int):
    # Existing demo rows keep their stored image URLs; only the bundled visuals change.
    if not 1 <= number <= 30:
        raise HTTPException(404, 'Demo image not found')
    return FileResponse(DEMO_ASSETS / f'property-{number:02}.webp', media_type='image/webp',
                        headers={'Cache-Control': 'public, max-age=3600'})


app.mount('/demo-assets', StaticFiles(directory=DEMO_ASSETS), name='demo-assets')

DIST = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
if (DIST / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
if (DIST / 'fonts').exists():
    app.mount('/fonts', StaticFiles(directory=DIST / 'fonts'), name='fonts')


@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith(('api/', 'webhooks/')):
        raise HTTPException(404, 'Endpoint not found')
    if not (DIST / 'index.html').exists():
        return PlainTextResponse('Run npm run build in frontend to prepare the dashboard.', status_code=503)
    return FileResponse(DIST / 'index.html')
