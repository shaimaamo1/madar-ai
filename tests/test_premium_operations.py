import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from backend import db
from tests.test_product import client, demo


def sandbox(client, text='New Cairo apartment, budget 5 million, 3 bedrooms', **values):
    return client.post('/api/sandbox/whatsapp', json={'contact_id': 'fictional_customer', 'event_id': db.uid(), 'text': text, 'consent': True, **values})


def bind(monkeypatch, state):
    monkeypatch.setenv('MADAR_INTEGRATION_TENANT_ID', state['company']['id'])
    monkeypatch.setenv('MADAR_BRIDGE_TOKEN', 'test-bridge-contract')
    return {'Authorization': 'Bearer test-bridge-contract'}


def test_whatsapp_sandbox_multiturn_inventory_and_no_provider_calls(client, monkeypatch):
    import backend.assistant as assistant
    def forbid_network(*args, **kwargs):
        raise AssertionError('Sandbox must not instantiate a provider client')
    monkeypatch.setenv('MADAR_AI_API_KEY', 'dummy-model-key')
    monkeypatch.setenv('MADAR_ALLOW_MODEL_USAGE', 'true')
    monkeypatch.setattr(assistant.httpx, 'AsyncClient', forbid_network)
    state = demo(client)
    first = sandbox(client, 'عايز شقة في التجمع، ميزانيتي ٥ مليون و٣ غرف').json()
    assert first['sandbox'] and first['mode'] == 'rules'
    assert first['matches'][0]['title'] == 'Palm Residence'
    assert first['intelligence']['score'] == 85
    second = sandbox(client, 'Can I book a viewing?').json()
    assert second['lead_id'] == first['lead_id']
    assert second['intelligence']['intent'] == 'appointment'
    fresh = client.get('/api/state').json()
    lead = next(l for l in fresh['leads'] if l['id'] == first['lead_id'])
    assert lead['budget'] == 5000000 and lead['assigned_to'] in [u['id'] for u in state['users']]
    assert len([m for m in fresh['messages'] if m['lead_id'] == lead['id']]) == 4
    assert not fresh['outbox']


def test_sandbox_replay_is_atomic_and_bound_to_contact(client):
    demo(client)
    first = sandbox(client, event_id='stable_event').json()
    repeat = sandbox(client, event_id='stable_event').json()
    assert repeat['duplicate'] and repeat['lead_id'] == first['lead_id']
    before = client.get('/api/state').json()
    conflict = sandbox(client, event_id='stable_event', contact_id='other_customer')
    assert conflict.status_code == 409
    after = client.get('/api/state').json()
    assert len(before['leads']) == len(after['leads']) and len(after['messages']) == len(before['messages'])


def test_human_handoff_persists_deduplicates_and_explicitly_resumes(client):
    demo(client)
    first = sandbox(client, 'عايز مستشار يكلمني').json()
    assert first['intelligence']['human_active']
    lead = first['lead_id']
    second = sandbox(client, 'New Cairo apartment 5 million').json()
    assert second['mode'] == 'human-handoff' and second['reply'] == ''
    state = client.get('/api/state').json()
    assert len([t for t in state['tasks'] if t['lead_id'] == lead and t['kind'] == 'handoff']) == 1
    client.post('/api/automation/tick')
    assert not any(o['lead_id'] == lead for o in client.get('/api/state').json()['outbox'])
    assert client.post('/api/leads/'+lead+'/handoff', json={'active': False}).status_code == 200
    third = sandbox(client, 'Apartment 3 bedrooms').json()
    assert third['reply'] and not third['intelligence']['human_active']
    assert any(a['action'] == 'conversation.resumed' for a in client.get('/api/state').json()['activities'])


def test_opt_out_reopt_in_and_operator_consent_guard(client):
    demo(client)
    first = sandbox(client).json()
    lead = first['lead_id']
    stopped = sandbox(client, 'متبعتش رسائل تاني').json()
    assert stopped['intelligence']['opted_out'] and not stopped['intelligence']['followup_eligible']
    assert client.patch('/api/leads/'+lead, json={'consent': True}).status_code == 422
    resumed = sandbox(client, 'موافق على المتابعة').json()
    assert resumed['intelligence']['consent'] and not resumed['intelligence']['opted_out']
    assert len([e for e in client.get('/api/state').json()['consent_events'] if e['lead_id'] == lead]) == 3


def test_real_workspace_refuses_fictional_sandbox(client):
    assert client.post('/api/auth/login', json={'workspace':'madar','email':'admin@madar.local','password':'TestOnlyPassword123!'}).status_code == 200
    assert sandbox(client).status_code == 403


def test_new_operational_controls_are_tenant_isolated(client, monkeypatch):
    first = demo(client)
    lead = sandbox(client).json()['lead_id']
    headers = bind(monkeypatch, first)
    assert client.post('/api/bridge/intelligence', headers=headers, json={'lead_id':lead}).status_code == 200
    assert client.post('/api/bridge/intelligence', json={'lead_id':lead}).status_code == 401
    client.post('/api/auth/logout')
    second = demo(client)
    assert client.get('/api/leads/'+lead+'/intelligence').status_code == 404
    assert client.post('/api/leads/'+lead+'/handoff', json={'active': True}).status_code == 404
    assert client.post('/api/bridge/intelligence', headers=headers, json={'lead_id':second['leads'][0]['id']}).status_code == 404


def test_bridge_booking_replay_and_changed_event_conflict(client, monkeypatch):
    state = demo(client)
    headers = bind(monkeypatch, state)
    lead = sandbox(client).json()['lead_id']
    fresh = client.get('/api/state').json()
    customer = next(l for l in fresh['leads'] if l['id'] == lead)
    at = (datetime.now(timezone.utc)+timedelta(days=2)).replace(hour=10,minute=0,second=0,microsecond=0).isoformat()
    booking = {'event_id':'viewing-confirmation','appointment':{'lead_id':lead,'property_id':state['properties'][0]['id'],'agent_id':customer['assigned_to'],'start_at':at}}
    first = client.post('/api/bridge/appointments', headers=headers, json=booking)
    assert first.status_code == 200, first.text
    repeat = client.post('/api/bridge/appointments', headers=headers, json=booking).json()
    assert repeat['duplicate'] and repeat['appointment']['id'] == first.json()['appointment']['id']
    assert len(client.get('/api/state').json()['appointments']) == len(state['appointments']) + 1
    booking['appointment']['notes'] = 'changed event'
    assert client.post('/api/bridge/appointments', headers=headers, json=booking).status_code == 409
    booking['event_id'] = 'another-confirmation'
    assert client.post('/api/bridge/appointments', headers=headers, json=booking).status_code == 409


def test_incident_redaction_dedupe_resolution_and_report(client, monkeypatch):
    state = demo(client)
    headers = bind(monkeypatch, state)
    data = {'event_id':'failure:wf:10','workflow_id':'wf','execution_id':'10'}
    first = client.post('/api/bridge/incidents', headers=headers, json=data).json()
    assert client.post('/api/bridge/incidents', headers=headers, json=data).json()['duplicate']
    assert client.post('/api/bridge/incidents', headers=headers, json={**data,'error':'secret-error-body'}).status_code == 422
    assert client.get('/api/operations').json()['open_incidents'] == 1
    assert client.patch('/api/incidents/'+first['incident_id']+'/resolve').status_code == 200
    assert client.get('/api/operations').json()['open_incidents'] == 0
    report = client.post('/api/bridge/report', headers=headers).json()
    assert report['metrics']['total_leads'] == len(state['leads'])
    assert 'revenue' in report['metrics'] and 'No forecast' in report['summary']


def test_reconciliation_does_not_retry_uncertain_requests(client, monkeypatch):
    state = demo(client); headers = bind(monkeypatch, state)
    lead = state['leads'][0]['id']
    with db.connection() as c:
        c.execute('INSERT INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(db.uid(),state['company']['id'],lead,'whatsapp','test','','uncertain-test','Uncertain',1,db.now(),'','redacted',db.now()))
    first = client.post('/api/bridge/reconcile', headers=headers).json()
    assert first['incidents_created'] == 1 and first['uncertain_deliveries_retried'] == 0
    assert client.post('/api/bridge/reconcile', headers=headers).json()['incidents_created'] == 0
    assert client.get('/api/state').json()['outbox'][0]['status'] == 'Uncertain'


def test_sandbox_contacts_cannot_escape_delivery_gate(client, monkeypatch):
    state = demo(client); bind(monkeypatch, state)
    lead = sandbox(client).json()['lead_id']
    assert client.post('/api/leads/'+lead+'/reply',json={'text':'Operator sandbox reply'}).status_code == 200
    monkeypatch.setenv('MADAR_ALLOW_EXTERNAL_SEND','true')
    def forbid_network(*args,**kwargs): raise AssertionError('Sandbox contact reached a live provider')
    monkeypatch.setattr('backend.integrations.httpx.AsyncClient',forbid_network)
    result = client.post('/api/integrations/dispatch').json()
    assert result['sent'] == 0 and result['held'] == 1
    assert 'Sandbox' in client.get('/api/state').json()['outbox'][0]['error']


@pytest.mark.parametrize('status',[200,429,400])
def test_official_whatsapp_templates_and_delivery_outcomes(client, monkeypatch, status):
    state=demo(client); bind(monkeypatch,state)
    monkeypatch.setenv('MADAR_ALLOW_EXTERNAL_SEND','true')
    monkeypatch.setenv('WHATSAPP_ACCESS_TOKEN','dummy-meta-token')
    monkeypatch.setenv('WHATSAPP_PHONE_NUMBER_ID','test-phone-id')
    lead=client.post('/api/leads',json={'name':'Approved fixture','source':'whatsapp','external_id':'fictional-provider-recipient','consent':True}).json()['lead']
    payload={'lead_id':lead['id'],'template_name':'viewing_confirmation','language':'en','parameters':['Fictional customer','Palm Residence']}
    assert client.post('/api/integrations/whatsapp/template',json=payload).status_code == 200
    requests=[]
    class MockMeta:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,**kwargs):
            requests.append((url,kwargs))
            return httpx.Response(status,json={'messages':[{'id':'mock-message-id'}]})
    monkeypatch.setattr('backend.integrations.httpx.AsyncClient',MockMeta)
    client.post('/api/integrations/dispatch')
    assert requests[0][0]=='https://graph.facebook.com/v23.0/test-phone-id/messages'
    sent=requests[0][1]['json']
    assert sent['type']=='template' and sent['template']['components'][0]['parameters'][1]['text']=='Palm Residence'
    out=client.get('/api/state').json()['outbox'][0]
    assert out['status']=={200:'Sent',429:'Retry',400:'Failed'}[status]


def test_whatsapp_service_window_and_signature_protection(client, monkeypatch):
    state=demo(client);bind(monkeypatch,state)
    monkeypatch.setenv('META_APP_SECRET','test-meta-signature-key')
    value={'messages':[{'type':'text','id':'fixture-event','from':'fixture-recipient','text':{'body':'New Cairo apartment budget 5 million'}}],'contacts':[{'profile':{'name':'Fixture lead'}}]}
    body=json.dumps({'object':'whatsapp_business_account','entry':[{'changes':[{'field':'messages','value':value}]}]}).encode()
    signature='sha256='+hmac.new(b'test-meta-signature-key',body,hashlib.sha256).hexdigest()
    assert client.post('/webhooks/meta',content=body).status_code == 401
    assert client.post('/webhooks/meta',content=body,headers={'x-hub-signature-256':signature}).status_code == 200
    assert client.post('/webhooks/meta',content=body,headers={'x-hub-signature-256':signature}).status_code == 200
    fresh=client.get('/api/state').json();lead=next(l for l in fresh['leads'] if l['external_id']=='fixture-recipient')
    assert len([m for m in fresh['messages'] if m['lead_id']==lead['id']])==2
    with db.connection() as c:
        c.execute("UPDATE messages SET created_at=? WHERE tenant_id=? AND lead_id=? AND direction='inbound'",((datetime.now(timezone.utc)-timedelta(hours=25)).isoformat(),state['company']['id'],lead['id']))
    monkeypatch.setenv('MADAR_ALLOW_EXTERNAL_SEND','true')
    assert client.post('/api/integrations/dispatch').json()['held']==1
    assert 'Outside messaging window' in client.get('/api/state').json()['outbox'][0]['error']


def test_additive_migration_preserves_existing_business_rows(client):
    state=demo(client)
    with db.connection() as c:
        original={name:c.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ('leads','properties','users','messages','deals')}
        c.execute('DROP TABLE conversation_controls');c.execute('DROP TABLE consent_events');c.execute('DROP TABLE automation_receipts');c.execute('DROP TABLE incidents')
        c.execute('DELETE FROM schema_migrations WHERE version=2')
    db.migrate();db.migrate()
    with db.connection() as c:
        assert original=={name:c.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in original}
        assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert [r[0] for r in c.execute('SELECT version FROM schema_migrations ORDER BY version')]==[1,2,3,4]
    assert client.get('/api/state').json()['company']['id']==state['company']['id']


def test_spoken_egyptian_preferences_and_inventory_constraints(client):
    demo(client)
    reply = sandbox(client, 'عايز شقة في التجمع بميزانية خمسة مليون، تلات غرف و١٨٠ متر وحمام سباحة').json()
    assert reply['matches'][0]['title'] == 'Palm Residence'
    lead = next(l for l in client.get('/api/state').json()['leads'] if l['id'] == reply['lead_id'])
    assert lead['budget'] == 5000000 and lead['bedrooms'] == 3 and lead['min_size'] == 180
    assert lead['amenities'] == ['Pool']
    no_match = sandbox(client, 'I need minimum 300 sqm').json()
    assert not no_match['matches']  # Never relax recorded requirements silently.


def test_fifth_transient_provider_failure_escalates_instead_of_staying_retry(client, monkeypatch):
    state=demo(client); bind(monkeypatch,state)
    monkeypatch.setenv('MADAR_ALLOW_EXTERNAL_SEND','true')
    monkeypatch.setenv('WHATSAPP_ACCESS_TOKEN','dummy-meta-token')
    monkeypatch.setenv('WHATSAPP_PHONE_NUMBER_ID','test-phone-id')
    lead=client.post('/api/leads',json={'name':'Retry fixture','source':'whatsapp','external_id':'fictional-recipient','consent':True}).json()['lead']
    client.post('/api/integrations/whatsapp/template',json={'lead_id':lead['id'],'template_name':'approved_fixture','language':'en'})
    with db.connection() as c:
        c.execute('UPDATE outbox SET attempts=4 WHERE tenant_id=? AND lead_id=?',(state['company']['id'],lead['id']))
    class MockMeta:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):return httpx.Response(503,json={})
    monkeypatch.setattr('backend.integrations.httpx.AsyncClient',MockMeta)
    client.post('/api/integrations/dispatch')
    assert client.get('/api/state').json()['outbox'][0]['status']=='Failed'
    assert client.get('/api/state').json()['outbox'][0]['attempts']==5
