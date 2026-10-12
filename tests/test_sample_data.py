"""Real-tenant sample safety and genuine Telegram business paths with fake providers."""
import json

import httpx
import pytest

from backend import db, sample_data
from tests.test_product import client, demo
from tests.test_telegram import bind, update, mock_provider


BUSINESS = ('users','properties','leads','messages','appointments','tasks','activities','conversation_controls')


def real(client):
    client.post('/api/auth/login', json={'workspace':'madar','email':'admin@madar.local','password':'TestOnlyPassword123!'}).raise_for_status()
    return client.get('/api/state').json()


def load(client):
    response = client.post('/api/sample-data/load', json={'confirmed':True})
    response.raise_for_status()
    return client.get('/api/state').json()


def snapshot(tenant, tables=BUSINESS):
    with db.connection() as c:
        return {table: [dict(r) for r in c.execute(f'SELECT * FROM {table} WHERE tenant_id=? ORDER BY '+('lead_id' if table=='conversation_controls' else 'id'), (tenant,))] for table in tables}


def test_import_relationships_images_idempotence_and_no_side_effects(client, monkeypatch):
    state = real(client); tenant = state['company']['id']
    existing = client.post('/api/leads',json={'name':'Existing real client','source':'telegram','external_id':'912345'}).json()['lead']
    client.post('/api/properties',json={'title':'Existing real property','location':'Maadi','price':2400000,'size':120}).raise_for_status()
    inventory=client.get('/api/state').json()['properties'][0]
    client.post('/api/appointments',json={'lead_id':existing['id'],'property_id':inventory['id'],'agent_id':state['user']['id'],'start_at':'2030-01-01T10:00:00+00:00'}).raise_for_status()
    before = snapshot(tenant)
    def forbidden(*args, **kwargs):
        raise AssertionError('Sample import cannot call providers')
    monkeypatch.setattr(httpx,'AsyncClient',forbidden)
    monkeypatch.setenv('MADAR_ALLOW_EXTERNAL_SEND','true')
    monkeypatch.setenv('MADAR_ALLOW_TELEGRAM_SEND','true')
    cfg = db.DB_PATH.parent/'telegram-private.json'
    # Treat any owner config file as opaque bytes, never opened by the import.
    monkeypatch.setenv('MADAR_INTEGRATION_TENANT_ID',tenant)
    cfg.write_text(json.dumps({'token':'fixture-private-token','enabled':True,'tenant_id':tenant,'transport':'polling'}))
    cfg.chmod(0o600)
    with db.connection() as c:
        c.execute('INSERT INTO telegram_polling VALUES(?,?,?,?,?,?,?)', ('fictional-bot',tenant,42,'existing-owner','2030-01-01T00:00:00+00:00','',''))
    unchanged = cfg.read_bytes()
    state = load(client)
    assert state['sample_data']['counts'] == {'messages':100,'tasks':20,'appointments':15,'conversation_controls':2,'activities':40,'leads':40,'properties':30,'users':5}
    leads = {l['id']:l for l in state['leads'] if l.get('sample')}
    props = {p['id']:p for p in state['properties'] if p.get('sample')}
    staff = {u['id']:u for u in state['users'] if u.get('sample')}
    assert len(leads)==40 and len(props)==30 and len(staff)==5
    assert len({m['lead_id'] for m in state['messages']})==25
    for lead in leads.values():
        assert lead['assigned_to'] in staff and not lead['phone']
        assert lead['external_id'].startswith('sandbox:sample-')
        assert lead['email'].endswith('@sample.invalid') and sample_data.LABEL in lead['name']
    for user in staff.values():
        assert not user['active'] and user['email'].endswith('@sample.invalid')
        assert 'password_hash' not in user
    for appointment in state['appointments']:
        if not appointment.get('sample'): continue
        assert appointment['sample'] and appointment['lead_id'] in leads
        assert appointment['property_id'] in props and appointment['agent_id'] in staff
        assert sample_data.LABEL in appointment['notes']
    for task in state['tasks']:
        if task.get('sample'): assert task['lead_id'] in leads and sample_data.LABEL in task['title']
    for message in state['messages']:
        assert message['sample'] and message['lead_id'] in leads and sample_data.LABEL in message['body']
    for prop in props.values():
        assert prop['reference'].startswith('SAMPLE-EG-') and sample_data.LABEL in prop['description']
        image = client.get(prop['image']); image.raise_for_status()
        assert image.headers['content-type']=='image/webp' and image.content[8:12]==b'WEBP'
    after = snapshot(tenant)
    for table, rows in before.items():
        for row in rows: assert row in after[table]
    for _ in range(2): client.post('/api/sample-data/load',json={'confirmed':True}).raise_for_status()
    assert snapshot(tenant)==after
    assert cfg.read_bytes()==unchanged
    assert not state['outbox']
    # Due fictional tasks, even with consent and globally authorized sends, cannot queue.
    with db.connection() as c:
        c.execute('DELETE FROM tasks WHERE tenant_id=? AND lead_id=?', (tenant, existing['id']))
    assert client.post('/api/automation/tick').json()['queued']==0
    assert not client.get('/api/state').json()['outbox']
    with db.connection() as c:
        assert not c.execute('SELECT 1 FROM telegram_contacts WHERE tenant_id=?',(tenant,)).fetchone()
        assert tuple(c.execute('SELECT * FROM telegram_polling WHERE tenant_id=?',(tenant,)).fetchone())==('fictional-bot',tenant,42,'existing-owner','2030-01-01T00:00:00+00:00','','')
        assert not c.execute('SELECT 1 FROM webhook_events WHERE tenant_id=?',(tenant,)).fetchone()


def test_confirmation_admin_tenant_scope_and_isolated_demo_preservation(client):
    state=real(client)
    assert client.post('/api/sample-data/load',json={'confirmed':False}).status_code==422
    assert client.post('/api/sample-data/load',json={'confirmed':'true'}).status_code==422
    assert client.post('/api/sample-data/load',json={'confirmed':True,'tenant_id':'unrelated'}).status_code==422
    assert client.post('/api/sample-data/remove',json={}).status_code==422
    assert not client.get('/api/state').json()['properties']
    isolated=demo(client); unchanged=snapshot(isolated['company']['id'])
    assert client.post('/api/sample-data/load',json={'confirmed':True}).status_code==403
    real(client); load(client)
    assert snapshot(isolated['company']['id'])==unchanged
    client.post('/api/users',json={'name':'Actual Agent','email':'agent@example.invalid','password':'TestAgentPassword123!','role':'agent'}).raise_for_status()
    client.post('/api/auth/login',json={'workspace':'madar','email':'agent@example.invalid','password':'TestAgentPassword123!'}).raise_for_status()
    assert client.get('/api/sample-data').status_code==403
    assert client.post('/api/sample-data/load',json={'confirmed':True}).status_code==403
    assert client.post('/api/sample-data/remove',json={'confirmed':True}).status_code==403
    real(client)
    client.post('/api/workspaces',json={'slug':'other-company','company_name':'Other Company','owner_name':'Other Owner','owner_email':'owner@other.invalid','owner_password':'OtherPassword123!'}).raise_for_status()
    client.post('/api/auth/login',json={'workspace':'other-company','email':'owner@other.invalid','password':'OtherPassword123!'}).raise_for_status()
    assert client.post('/api/sample-data/load',json={'confirmed':True}).status_code==403


def test_sample_staff_cannot_authenticate_even_if_activated_by_database_operator(client):
    real(client); state=load(client); staff=next(u for u in state['users'] if u.get('sample'))
    from backend.security import hasher, login_session
    from fastapi import Response
    with db.connection() as c:
        c.execute('UPDATE users SET active=1,password_hash=? WHERE id=?',(hasher.hash('ForbiddenPassword123!'),staff['id']))
        response=Response(); login_session(c,staff['id'],response)
        cookie=response.headers['set-cookie'].split(';')[0].split('=',1)[1]
    assert client.post('/api/auth/login',json={'workspace':'madar','email':staff['email'],'password':'ForbiddenPassword123!'}).status_code==401
    client.cookies.set('madar_session',cookie)
    assert client.get('/api/state').status_code==401


def test_sample_vs_real_analytics_and_safe_removal(client):
    real(client)
    actual=client.post('/api/leads',json={'name':'Actual customer','source':'telegram','external_id':'101'}).json()['lead']
    load(client)
    client.post('/api/deals',json={'lead_id':actual['id'],'amount':5000000,'commission':100000,'status':'Won'}).raise_for_status()
    metrics=client.get('/api/analytics').json()
    assert metrics['total_leads']==1 and metrics['sources']=={'telegram':1}
    assert metrics['sample_counts']['leads']==40 and metrics['excludes_sample_activity']
    assert metrics['appointments']==0 and metrics['followups']['total']==1
    assert metrics['revenue']==100000 and metrics['sales_volume']==5000000
    client.post('/api/sample-data/remove',json={'confirmed':True}).raise_for_status()
    state=client.get('/api/state').json()
    assert not state['sample_data']['loaded'] and not state['sample_data']['counts']
    assert [l['id'] for l in state['leads']]==[actual['id']]
    assert not state['properties'] and not state['appointments'] and len(state['users'])==1
    assert client.get('/api/analytics').json()['revenue']==100000
    assert client.post('/api/sample-data/remove',json={'confirmed':True}).status_code==200
    load(client)
    assert client.get('/api/state').json()['sample_data']['counts']['leads']==40


def test_real_telegram_crm_inbox_booking_and_dependent_removal_block(client,monkeypatch):
    real(client); state=load(client); headers=bind(monkeypatch,state)
    def incoming(event):
        response=client.post('/webhooks/telegram',json=event,headers=headers)
        response.raise_for_status(); return response.json()
    event=update(500,'Buy apartment New Cairo budget 5 million 3 bedrooms')
    incoming(event)
    after=client.get('/api/state').json()
    lead=next(l for l in after['leads'] if l['external_id']=='101')
    assert not lead.get('sample') and lead['id'] not in {l['id'] for l in state['leads']}
    assert lead['assigned_to']==state['user']['id'] and lead['budget']==5000000
    assert len([l for l in after['leads'] if not l.get('sample')])==1
    messages=[m for m in after['messages'] if m['lead_id']==lead['id']]
    assert {m['direction'] for m in messages}=={'inbound','outbound'}
    assert any('Palm Residence' in m['body'] and 'Sample / Fictional' in m['body'] for m in messages)
    incoming(event)
    assert len(client.get('/api/state').json()['messages'])==len(after['messages'])
    def button():
        newest=max(client.get('/api/state').json()['outbox'],key=lambda row:row['created_at'])
        return json.loads(newest['template'])['inline_keyboard'][0][0]['callback_data']
    def callback(i):
        message=update(i)['message']
        incoming({'update_id':i,'callback_query':{'id':f'fixture-{i}','data':button(),'from':message['from'],'message':message}})
    # Pending Telegram selections are preserved before any booking is committed.
    assert client.post('/api/sample-data/remove',json={'confirmed':True}).status_code==409
    callback(501); callback(502)
    assert len(client.get('/api/state').json()['appointments'])==15
    callback(503)
    final=client.get('/api/state').json()
    booked=next(a for a in final['appointments'] if a['lead_id']==lead['id'])
    assert not booked.get('sample') and booked['agent_id']==state['user']['id']
    assert booked['property_id'] in {p['id'] for p in state['properties'] if p.get('sample')}
    assert 'Sample / Fictional property' in booked['notes']
    assert any(a['entity_id']==lead['id'] and a['action']=='lead.viewing_confirmed' for a in final['activities'])
    assert any(a['entity_id']==booked['id'] and a['action']=='appointment.booked' for a in final['activities'])
    assert next(l for l in final['leads'] if l['id']==lead['id'])['stage']=='Viewing'
    assert any(t['lead_id']==lead['id'] and not t.get('sample') for t in final['tasks'])
    metrics=client.get('/api/analytics').json()
    assert metrics['total_leads']==1 and metrics['appointments']==1 and metrics['pipeline']['Viewing']==1
    before=snapshot(state['company']['id'])
    assert client.post('/api/sample-data/remove',json={'confirmed':True}).status_code==409
    assert snapshot(state['company']['id'])==before
    assert client.post('/api/sample-data/load',json={'confirmed':True}).status_code==200
    assert snapshot(state['company']['id'])==before
    delivered=[]
    def provider(request):
        body=json.loads(request.content); delivered.append(body)
        assert str(body['chat_id'])=='101'
        return httpx.Response(200,json={'ok':True,'result':{'message_id':len(delivered)}})
    mock_provider(monkeypatch,provider)
    monkeypatch.setenv('MADAR_ALLOW_TELEGRAM_SEND','true')
    client.post('/api/integrations/dispatch').raise_for_status()
    assert any('Your viewing is confirmed' in body['text'] for body in delivered)
    assert any('Sample / Fictional property' in body['text'] for body in delivered)


def test_sample_delivery_block_survives_contact_edit(client,monkeypatch):
    real(client); state=load(client); bind(monkeypatch,state)
    sample=next(l for l in state['leads'] if l.get('sample') and l['source']=='telegram')
    # Defense in depth: even an erroneous direct DB rewrite cannot send to a sample lead.
    with db.connection() as c:
        c.execute('UPDATE leads SET external_id=?,consent=1,opted_out=0 WHERE id=?',('999',sample['id']))
        c.execute('INSERT INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(db.uid(),state['company']['id'],sample['id'],'telegram','Never deliver','', 'manual:test','Pending',0,db.now(),'','',db.now()))
    mock_provider(monkeypatch,lambda r: pytest.fail('Fictional lead must never reach Telegram'))
    monkeypatch.setenv('MADAR_ALLOW_TELEGRAM_SEND','true')
    assert client.post('/api/integrations/dispatch').json()['sent']==0
    assert next(o for o in client.get('/api/state').json()['outbox'] if o['lead_id']==sample['id'])['status']=='Held'
    # A contact with additional untracked outbox data is protected from reset cascades.
    assert client.post('/api/sample-data/remove',json={'confirmed':True}).status_code==409


def test_import_collision_rolls_back_without_overwriting_real_records(client):
    state=real(client); tenant=state['company']['id']
    with db.connection() as c:
        c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',(f'sample-agent-{tenant}-001',tenant,'existing@real.invalid','Existing protected staff','agent','!inactive',0))
    before=snapshot(tenant)
    assert client.post('/api/sample-data/load',json={'confirmed':True}).status_code==409
    assert snapshot(tenant)==before
    assert not client.get('/api/sample-data').json()['loaded']


def test_removal_guards_legacy_cross_tenant_cascade_references(client):
    real(client); state=load(client); lead=state['leads'][0]
    foreign=demo(client)
    with db.connection() as c:
        # Simulate a legacy bad FK; normal APIs reject cross-tenant IDs.
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)', (db.uid(),foreign['company']['id'],lead['id'],'inbound','website','Protected legacy message','',db.now()))
    unchanged=snapshot(foreign['company']['id'])
    real(client)
    assert client.post('/api/sample-data/remove',json={'confirmed':True}).status_code==409
    assert snapshot(foreign['company']['id'])==unchanged


def test_manual_sample_reply_cannot_queue_external_delivery(client):
    real(client); state=load(client)
    lead=next(l for l in state['leads'] if l['source']=='telegram')
    response=client.post('/api/leads/'+lead['id']+'/reply',json={'text':'Fictional presentation response'})
    response.raise_for_status()
    assert response.json()['external_delivery']=='sample inbox only; external delivery blocked'
    assert not client.get('/api/state').json()['outbox']
    assert client.post('/api/automation/tick').json()['queued']==0
    # Preserve the newly added history; removing seed parents must not cascade it.
    assert client.post('/api/sample-data/remove',json={'confirmed':True}).status_code==409


def test_public_customer_recommendations_and_booking_disclose_fictional_inventory(client):
    real(client); state=load(client)
    inquiry=client.post('/api/public/chat',json={'tenant_slug':'madar','name':'Website fixture buyer','text':'Buy apartment New Cairo budget 5 million 3 bedrooms'})
    inquiry.raise_for_status(); result=inquiry.json()
    assert 'Sample / Fictional' in result['reply'] and all(p['sample'] for p in result['matches'])
    request={'tenant_slug':'madar','session':result['session'],'property_id':result['matches'][0]['id']}
    slots=client.post('/api/public/slots',json=request); slots.raise_for_status()
    booking=client.post('/api/public/book',json={**request,'start_at':slots.json()['slots'][0]['start_at']})
    booking.raise_for_status()
    saved=next(a for a in client.get('/api/state').json()['appointments'] if not a.get('sample'))
    assert 'Sample / Fictional property' in saved['notes']
    assert saved['start_at']==booking.json()['start_at']
    assert not saved.get('sample')
