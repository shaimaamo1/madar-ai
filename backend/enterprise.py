"""Scoped orchestration, durable business artifacts and truthful runtime evidence."""
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field

from . import db
from .domain import book, create_lead, match_properties, record, require, tick
from .models import Booking, LeadInput, Model
from .operations import bridge_tenant, lead_intelligence, operation_status, set_handoff
from .security import admin, current_user, digest
from .urls import service_url

router = APIRouter()
KINDS = ('intake', 'qualification', 'matching', 'appointment', 'followup', 'conversation', 'handoff', 'reporting')
Kind = Literal['intake', 'qualification', 'matching', 'appointment', 'followup', 'conversation', 'handoff', 'reporting']


class Envelope(Model):
    kind: Kind
    event_id: str = Field(min_length=1, max_length=200)
    lead_id: str = Field(default='', max_length=100)
    run_id: str = Field(default='', max_length=100)
    run_token: str = Field(default='', max_length=100)
    lead: LeadInput | None = None
    text: str = Field(default='', max_length=4000)
    appointment: Booking | None = None


class Commit(Envelope):
    execution_id: str = Field(default='', pattern=r'^[a-zA-Z0-9_-]{0,100}$')
    analysis: dict = Field(default_factory=dict)


class Failure(Envelope):
    execution_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    reason: Literal['validation_failed','backend_failed']


@router.post('/api/bridge/enterprise/failure')
def record_failure(data: Failure, request: Request):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant, run = scope(c, request, data)
        event = 'enterprise-failure:' + hashlib.sha256((data.event_id + ':' + data.kind).encode()).hexdigest()
        identifier = db.uid()
        inserted = c.execute('INSERT OR IGNORE INTO incidents VALUES(?,?,?,?,?,?,?,?)',
                             (identifier, tenant, event, '', data.execution_id, 'workflow_failure', 'Open', db.now()))
        if run:
            c.execute("UPDATE demo_runs SET status='Failed',capability_hash='',execution_id=?,updated_at=? WHERE id=?", (data.execution_id, db.now(), run['id']))
        if inserted.rowcount:
            db.audit(c, tenant, 'n8n', 'enterprise.failed', identifier, data.kind + ':' + data.reason)
    return {'status':'Failed','reason':data.reason,'duplicate':not bool(inserted.rowcount)}


def scope(c, request, data):
    bound = bridge_tenant(request, c)  # Always authenticate the server bridge first.
    if not data.run_id:
        if data.run_token:
            raise HTTPException(403, 'Invalid demo capability')
        return bound, None
    run = c.execute('SELECT r.*,t.demo FROM demo_runs r JOIN tenants t ON t.id=r.tenant_id WHERE r.id=?', (data.run_id,)).fetchone()
    if not run or not run['demo'] or run['status'] != 'Running' or not data.run_token or not secrets.compare_digest(run['capability_hash'], digest(data.run_token)) or datetime.fromisoformat(run['expires_at']) <= datetime.now(timezone.utc):
        raise HTTPException(403, 'Invalid or expired demo capability')
    # Demo callers cannot inject customer contact data or target another lead.
    if data.lead is not None or data.appointment is not None or data.text:
        raise HTTPException(403, 'Demo scenario input is server controlled')
    if data.event_id != run['id']:
        raise HTTPException(403, 'Demo event does not belong to this run')
    lead = c.execute("SELECT lead_id FROM enterprise_artifacts WHERE run_id=? AND tenant_id=? AND kind='intake'", (run['id'], run['tenant_id'])).fetchone()
    if data.lead_id and (not lead or lead[0] != data.lead_id):
        raise HTTPException(403, 'Demo lead does not belong to this run')
    return run['tenant_id'], run


def snapshot(c, tenant, data, run=None):
    lead_id = data.lead_id
    if run and not lead_id:
        row = c.execute("SELECT lead_id FROM enterprise_artifacts WHERE run_id=? AND tenant_id=? AND kind='intake'", (run['id'], tenant)).fetchone()
        lead_id = row[0] if row else ''
    lead = require(c, 'leads', tenant, lead_id) if lead_id else None
    if data.kind not in ('intake', 'followup', 'reporting') and not lead:
        raise HTTPException(422, 'A customer reference is required')
    cfg = db.settings(c, tenant)
    arrays = {table: [record(r) for r in c.execute(f'SELECT * FROM {table} WHERE tenant_id=?', (tenant,))] for table in ('leads', 'properties', 'appointments', 'tasks', 'deals', 'conversation_controls')}
    users = [dict(r) for r in c.execute('SELECT id,name,role,active FROM users WHERE tenant_id=?', (tenant,))]
    messages = [dict(r) for r in c.execute('SELECT direction,body,channel,created_at FROM messages WHERE tenant_id=? AND lead_id=? ORDER BY created_at DESC LIMIT 30', (tenant, lead_id))] if lead else []
    control = next((r for r in arrays['conversation_controls'] if r['lead_id'] == lead_id), {})
    matches = match_properties(c, tenant, lead) if lead else []
    body = data.model_dump()
    if run:
        body['lead_id'] = lead_id
        if data.kind == 'intake':
            body['lead'] = LeadInput(name='Enterprise demo customer', source='whatsapp', external_id='sandbox:demo:' + run['id'], consent=True).model_dump()
            body['text'] = 'عايز شقة في التجمع، ميزانيتي ٥ مليون و٣ غرف'
    return {'request': data.model_dump(), 'inquiry': body, 'lead': lead, 'settings': {k:cfg[k] for k in ('currency','timezone','business_start','business_end','followup_hours')},
            **arrays, 'agents': users, 'messages': messages, 'matches': matches, 'control': control,
            'safety': operation_status(c, tenant), 'generated_at': db.now(), 'analysis': {}, 'demo': bool(run)}


@router.post('/api/bridge/enterprise/context')
def context(data: Envelope, request: Request):
    with db.connection() as c:
        tenant, run = scope(c, request, data)
        return snapshot(c, tenant, data, run)


def reserve_demo(c, tenant, lead, matches, cfg):
    if not matches:
        raise HTTPException(409, 'Demo inventory has no suitable available property')
    zone = ZoneInfo(cfg['timezone'])
    for day in range(1, 8):
        for hour in range(cfg['business_start'], cfg['business_end']):
            start = (datetime.now(zone) + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            try:
                return book(c, tenant, {'lead_id':lead['id'],'property_id':matches[0]['id'],'agent_id':lead['assigned_to'],'start_at':start.isoformat(),'notes':'Explicit fictional full-demo viewing'}, 'n8n-demo')
            except HTTPException as error:
                if error.status_code != 409:
                    raise
    raise HTTPException(409, 'No conflict-free demo viewing is available')


@router.post('/api/bridge/enterprise/commit')
@db.serialized_conversation
async def commit(data: Commit, request: Request):
    # Analysis is an advisory artifact, never authority for consent, assignment or booking.
    if len(json.dumps(data.analysis)) > 32000:
        raise HTTPException(422, 'Analysis exceeds the artifact limit')
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant, run = scope(c, request, data)
        stable = data.model_dump(exclude={'run_token','execution_id','analysis'})
        signature = hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()
        previous = c.execute('SELECT * FROM enterprise_artifacts WHERE tenant_id=? AND event_id=? AND kind=?', (tenant,data.event_id,data.kind)).fetchone()
        if previous:
            if previous['request_hash'] != signature:
                raise HTTPException(409, 'Event ID was reused with different enterprise input')
            return dict(json.loads(previous['result']), duplicate=True, run_token=data.run_token)
        if run:
            done = {r[0] for r in c.execute('SELECT kind FROM enterprise_artifacts WHERE run_id=?', (run['id'],))}
            expected = KINDS[len(done)] if len(done) < len(KINDS) else None
            if data.kind != expected:
                raise HTTPException(409, 'Demo steps must execute in the documented order')
        view = snapshot(c, tenant, data, run)
        lead = view['lead']
        result = {'kind':data.kind,'event_id':data.event_id,'run_id':data.run_id,'lead_id':lead['id'] if lead else '', 'duplicate':False, 'external_messages_sent':0, 'mode':'deterministic', 'analysis':data.analysis}
        if data.kind == 'intake':
            from .assistant import respond
            envelope = view['inquiry']
            if not envelope['lead'] or not envelope['text']:
                raise HTTPException(422, 'Intake requires customer data and a message')
            source = envelope['lead']['source']
            receipt = None if run else c.execute('INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?)', (db.uid(),tenant,source,data.event_id,db.now()))
            if receipt is not None and not receipt.rowcount:
                # Share the existing provider/normalized receipt boundary. A
                # previously processed event must never add another message.
                linked = c.execute('SELECT lead_id FROM messages WHERE tenant_id=? AND channel=? AND external_id=? UNION SELECT lead_id FROM outbox WHERE tenant_id=? AND dedupe_key=? LIMIT 1', (tenant,source,data.event_id,tenant,'event:'+source+':'+data.event_id)).fetchone()
                result.update(duplicate=True,created=False,lead_id=linked[0] if linked else '',reply='',mode='recorded-replay')
            else:
                lead, created = create_lead(c, tenant, envelope['lead'], 'n8n')
                result.update(lead_id=lead['id'], created=created)
                reply = await respond(c, tenant, lead, envelope['text'], source, 'enterprise:' + data.event_id if run else data.event_id, allow_model=False if run else True)
                result['reply'] = reply['reply']
                result['mode'] = reply['mode']
                if not run and reply['reply'] and source != 'website':
                    from .main import queue_message
                    queue_message(c,tenant,lead['id'],source,reply['reply'],'event:'+source+':'+data.event_id)
        elif data.kind == 'qualification':
            result['intelligence'] = lead_intelligence(c, tenant, lead['id'])
        elif data.kind == 'matching':
            result['recommendations'] = [{'id':p['id'],'title':p['title'],'price':p['price'],'reasons':p['reasons'],'match_score':p['match_score']} for p in view['matches']]
            result['no_match'] = not bool(view['matches'])
        elif data.kind == 'appointment':
            if run:
                result['appointment'] = reserve_demo(c, tenant, lead, view['matches'], view['settings'])
            elif data.appointment:
                if data.appointment.lead_id != lead['id']:
                    raise HTTPException(422, 'Booking customer reference differs')
                result['appointment'] = book(c, tenant, data.appointment.model_dump(), 'n8n')
            else:
                raise HTTPException(422, 'An explicit appointment is required')
        elif data.kind == 'followup':
            result.update(tick(c, tenant))
        elif data.kind == 'conversation':
            from .ai_agents import agent_suite
            result['agents'] = await agent_suite(c, tenant, lead, 'ar' if run else 'en', allow_model=False if run else True)
            result['draft'] = result['agents']['reply_drafting']['draft']
            result['requires_human_approval'] = True
        elif data.kind == 'handoff':
            set_handoff(c, tenant, lead['id'], True, 'Qualification escalation', 'n8n')
            due = (datetime.now(timezone.utc) + timedelta(minutes=30 if lead['score'] >= 65 else 120)).isoformat()
            c.execute('INSERT INTO adviser_cases VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(tenant_id,lead_id) DO NOTHING', (db.uid(),tenant,lead['id'],lead['assigned_to'],'Open','High' if lead['score']>=65 else 'Normal',due,db.now(),db.now()))
            result['case'] = dict(c.execute('SELECT * FROM adviser_cases WHERE tenant_id=? AND lead_id=?', (tenant,lead['id'])).fetchone())
        else:
            from .main import report
            result['report'] = report({'tenant_id':tenant})
        identifier = db.uid()
        c.execute('INSERT INTO enterprise_artifacts VALUES(?,?,?,?,?,?,?,?,?,?)', (identifier,tenant,data.run_id or None,data.event_id,data.kind,result['lead_id'] or None,signature,json.dumps(result,ensure_ascii=False),data.execution_id,db.now()))
        db.audit(c,tenant,'n8n','enterprise.'+data.kind,identifier,'Demo sandbox' if run else 'Managed orchestration')
        if run:
            c.execute('UPDATE demo_runs SET updated_at=? WHERE id=?', (db.now(),run['id']))
        return dict(result, run_token=data.run_token)


@router.get('/api/enterprise/artifacts')
def artifacts(user=Depends(current_user)):
    with db.connection() as c:
        return [dict(r, result=json.loads(r['result'])) for r in c.execute('SELECT id,kind,run_id,event_id,result,execution_id,created_at FROM enterprise_artifacts WHERE tenant_id=? ORDER BY created_at DESC LIMIT 50', (user['tenant_id'],))]


@router.patch('/api/adviser-cases/{case_id}/{action}')
def update_case(case_id: str, action: Literal['acknowledge','resolve'], user=Depends(current_user)):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        case = require(c,'adviser_cases',user['tenant_id'],case_id)
        if user['role'] != 'admin' and case['agent_id'] != user['id']:
            raise HTTPException(403, 'Only the assigned adviser can update this case')
        if case['status'] == 'Resolved':
            return {'status':'Resolved'}
        status = 'Acknowledged' if action == 'acknowledge' else 'Resolved'
        c.execute('UPDATE adviser_cases SET status=?,updated_at=? WHERE id=? AND tenant_id=?', (status,db.now(),case_id,user['tenant_id']))
        db.audit(c,user['tenant_id'],user['id'],'case.'+action,case_id)
    return {'status':status}  # Resolving a case does not silently resume AI ownership.


@router.post('/api/demo/runs')
def start_run(user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute('SELECT demo FROM tenants WHERE id=?', (user['tenant_id'],)).fetchone()[0]:
            raise HTTPException(403, 'Full demo requires a fictional demo workspace')
        c.execute("UPDATE demo_runs SET status='Expired',capability_hash='' WHERE tenant_id=? AND status IN ('Queued','Running','Awaiting verification') AND expires_at<?", (user['tenant_id'],db.now()))
        old = c.execute("SELECT id,status FROM demo_runs WHERE tenant_id=? AND status IN ('Queued','Running','Awaiting verification')", (user['tenant_id'],)).fetchone()
        if old:
            return dict(old, duplicate=True)
        identifier = db.uid()
        c.execute('INSERT INTO demo_runs VALUES(?,?,?,?,?,?,?,?,?)', (identifier,user['tenant_id'],user['id'],'Queued','',(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(),'',db.now(),db.now()))
        db.audit(c,user['tenant_id'],user['id'],'demo.queued',identifier)
    return {'id':identifier,'status':'Queued','duplicate':False}


@router.get('/api/demo/runs')
def runs(user=Depends(current_user)):
    with db.connection() as c:
        c.execute("UPDATE demo_runs SET status='Expired',capability_hash='',updated_at=? WHERE tenant_id=? AND status IN ('Queued','Running','Awaiting verification') AND expires_at<?", (db.now(),user['tenant_id'],db.now()))
        result=[]
        for row in c.execute('SELECT id,status,execution_id,expires_at,created_at,updated_at FROM demo_runs WHERE tenant_id=? ORDER BY created_at DESC LIMIT 10', (user['tenant_id'],)):
            steps = [dict(r) for r in c.execute('SELECT kind,execution_id,created_at FROM enterprise_artifacts WHERE tenant_id=? AND run_id=? ORDER BY created_at', (user['tenant_id'],row['id']))]
            result.append(dict(row,steps=steps))
        return result


@router.post('/api/bridge/demo/claim')
def claim(request: Request):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        bridge_tenant(request,c)
        row = c.execute("SELECT r.* FROM demo_runs r JOIN tenants t ON t.id=r.tenant_id WHERE r.status='Queued' AND t.demo=1 AND r.expires_at>? ORDER BY r.created_at LIMIT 1", (db.now(),)).fetchone()
        if not row:
            raise HTTPException(409, 'No queued fictional demo is available')
        token = secrets.token_urlsafe(32)
        c.execute("UPDATE demo_runs SET status='Running',capability_hash=?,updated_at=? WHERE id=?", (digest(token),db.now(),row['id']))
        return {'run_id':row['id'],'run_token':token,'event_id':row['id'],'lead_id':'','kind':'intake'}


class Finish(Model):
    run_id: str
    run_token: str
    execution_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')


@router.post('/api/bridge/demo/complete')
def complete_run(data: Finish, request: Request):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant, run = scope(c,request,Envelope(kind='reporting',event_id=data.run_id,run_id=data.run_id,run_token=data.run_token))
        done = {r[0] for r in c.execute('SELECT kind FROM enterprise_artifacts WHERE tenant_id=? AND run_id=?', (tenant,run['id']))}
        if done != set(KINDS):
            raise HTTPException(409, 'Not all business steps have completed')
        c.execute("UPDATE demo_runs SET status='Awaiting verification',execution_id=?,capability_hash='',updated_at=? WHERE id=?", (data.execution_id,db.now(),run['id']))
    return {'run_id':data.run_id,'status':'Awaiting verification','execution_id':data.execution_id,'steps':len(done)}


async def n8n_read(path):
    if os.getenv('N8N_ENABLED') != 'true' or not os.getenv('N8N_API_KEY'):
        return None
    base = service_url(os.getenv('N8N_CONTAINER_URL') or os.getenv('N8N_BASE_URL',''), 'n8n')
    async with httpx.AsyncClient(timeout=5,trust_env=False,follow_redirects=False) as client:
        response = await client.get(base+'/api/v1/'+path, headers={'X-N8N-API-KEY':os.environ['N8N_API_KEY']})
        response.raise_for_status()
        return response.json()


@router.post('/api/demo/runs/{run_id}/verify')
async def verify_run(run_id: str, user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        run = require(c,'demo_runs',user['tenant_id'],run_id)
    if run['status'] == 'Verified':
        return {'status':'Verified','execution_id':run['execution_id']}
    if run['status'] != 'Awaiting verification':
        raise HTTPException(409, 'Demo execution has not completed')
    try:
        # Full Demo stores fictional success evidence only. Inspect internally,
        # never return the execution payload/capability to the browser or logs.
        execution = await n8n_read('executions/'+run['execution_id']+'?includeData=true')
        if not execution:
            return {'status':'Awaiting verification','reason':'n8n API access is not configured'}
        workflow = await n8n_read('workflows/'+str(execution.get('workflowId','')))
        started = datetime.fromisoformat(str(execution.get('startedAt', '')).replace('Z', '+00:00'))
        if not workflow or workflow.get('name') != 'MADAR Full Demo' or execution.get('status') != 'success' or not execution.get('finished') or started < datetime.fromisoformat(run['created_at']):
            return {'status':'Awaiting verification','reason':'n8n has not confirmed a successful full-demo execution'}
        steps = execution['data']['resultData']['runData']
        completion = steps['Record actual execution reference'][0]['data']['main'][0][0]['json']
        if completion.get('run_id') != run_id or str(completion.get('execution_id')) != run['execution_id']:
            return {'status':'Awaiting verification','reason':'n8n execution does not belong to this demo run'}
    except (httpx.HTTPError,ValueError,KeyError):
        return {'status':'Awaiting verification','reason':'n8n execution could not be verified; diagnostic payload omitted'}
    with db.connection() as c:
        c.execute("UPDATE demo_runs SET status='Verified',updated_at=? WHERE id=? AND tenant_id=? AND status='Awaiting verification'", (db.now(),run_id,user['tenant_id']))
    return {'status':'Verified','execution_id':run['execution_id']}


@router.get('/api/system-health')
async def health(user=Depends(current_user)):
    checks=[{'component':'Backend','status':'PASS','detail':'Authenticated API responded'}]
    with db.connection() as c:
        checks.append({'component':'Database','status':'PASS' if c.execute('PRAGMA quick_check').fetchone()[0]=='ok' else 'FAIL','detail':'SQLite quick integrity check'})
        safety = operation_status(c,user['tenant_id'])
        checks.append({'component':'Customer messaging','status':'PASS' if not safety['external_send_enabled'] else 'NOT VERIFIED','detail':'Disabled by default' if not safety['external_send_enabled'] else 'Authorization flag enabled; delivery not verified'})
        pending = c.execute("SELECT COUNT(*) FROM adviser_cases WHERE tenant_id=? AND status<>'Resolved' AND due_at<?", (user['tenant_id'],db.now())).fetchone()[0]
        checks.append({'component':'Adviser SLA','status':'FAIL' if pending else 'PASS','detail':'{count} overdue cases','count':pending})
    try:
        remote = await n8n_read('workflows?limit=100')
        checks.append({'component':'n8n API','status':'PASS' if remote is not None else 'NOT VERIFIED','detail':'Workflow read access verified' if remote is not None else 'Local API access is not configured'})
    except (httpx.HTTPError,ValueError):
        checks.append({'component':'n8n API','status':'FAIL','detail':'Connection or access failed; response omitted'})
    from .telegram import configuration, status
    telegram_status = status(configuration()) if user['tenant_id'] == os.getenv('MADAR_INTEGRATION_TENANT_ID') else {}
    checks.append({'component':'Telegram polling','status':'PASS' if telegram_status.get('polling_active') else 'NOT VERIFIED', 'detail':'Polling read access verified' if telegram_status.get('polling_active') else 'Connect your dedicated bot locally'})
    checks.append({'component':'Telegram delivery','status':'NOT VERIFIED' if telegram_status.get('enabled') else 'PASS', 'detail':'Telegram delivery authorized; receiving and replying to a real message still needs verification' if telegram_status.get('enabled') else 'Telegram delivery disabled independently'})
    checks += [{'component':'Docker Desktop','status':'NOT VERIFIED','detail':'Requires trusted Windows launcher evidence'}, {'component':'Windows execution','status':'NOT VERIFIED','detail':'Requires execution on Windows'}, {'component':'Meta delivery','status':'NOT VERIFIED','detail':'Real customer delivery has not been authorized'}]
    return {'checked_at':db.now(),'checks':checks,'safety':safety,'model_configured':bool(os.getenv('MADAR_AI_API_KEY')),'paid_model_enabled':os.getenv('MADAR_ALLOW_MODEL_USAGE')=='true'}
