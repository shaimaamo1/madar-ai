import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from backend import db
from backend.telegram import configuration, store
from backend.telegram_polling import acquire, consume, cycle, release
from tests.test_product import client, demo

REAL_ASYNC_CLIENT = httpx.AsyncClient

TOKEN = '123456:fictional_test_bot_token_1234567890'


def bind(monkeypatch, state, enabled=False):
    monkeypatch.setenv('MADAR_INTEGRATION_TENANT_ID', state['company']['id'])
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', 'fictional-webhook-secret')
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', TOKEN)
    monkeypatch.setenv('MADAR_ALLOW_TELEGRAM_SEND', 'true' if enabled else 'false')
    return {'x-telegram-bot-api-secret-token': 'fictional-webhook-secret'}


def update(identifier=1, text='/start', chat=101, language='en'):
    return {'update_id': identifier, 'message': {'text': text, 'chat': {'id': chat, 'type': 'private'}, 'from': {'id': chat, 'first_name': 'Fictional customer', 'language_code': language}}}


def sandbox(client, identifier, text='/properties', callback='', chat=101, language='en'):
    response = client.post('/api/sandbox/telegram', json={'update_id':identifier, 'chat_id':chat, 'text':text, 'callback_data':callback, 'language':language})
    assert response.status_code == 200, response.text
    return response.json()


def real_admin(client, monkeypatch):
    assert client.post('/api/auth/login', json={'workspace':'madar','email':'admin@madar.local','password':'TestOnlyPassword123!'}).status_code == 200
    state = client.get('/api/state').json()
    bind(monkeypatch, state)
    return state


def mock_provider(monkeypatch, handler):
    original = REAL_ASYNC_CLIENT
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


def test_private_setup_authorization_and_no_credential_echo(client, monkeypatch):
    demo(client)
    assert client.put('/api/telegram/setup', json={'token':TOKEN}).status_code == 403
    state = real_admin(client, monkeypatch)
    result = client.put('/api/telegram/setup', json={'token':TOKEN})
    assert result.status_code == 200 and not result.json()['enabled']
    assert TOKEN not in result.text and 'secret' not in result.text
    path = db.DB_PATH.parent/'telegram-private.json'
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text())['token'] == TOKEN
    before = path.read_bytes()
    assert client.put('/api/telegram/setup', json={'token':TOKEN, 'public_origin':'http://localhost:8000'}).status_code == 422
    assert path.read_bytes() == before
    invalid = client.put('/api/telegram/setup', json={'token':{'value':TOKEN}})
    assert invalid.status_code == 422 and TOKEN not in invalid.text
    assert client.put('/api/telegram/delivery', json={'authorized':True}).status_code == 422
    demo(client)
    assert client.get('/api/telegram/setup').status_code == 403


def test_connect_does_not_send_or_remove_webhooks_without_authorization(client, monkeypatch):
    real_admin(client, monkeypatch)
    client.put('/api/telegram/setup', json={'token':TOKEN})
    calls=[]
    def handler(request):
        method = request.url.path.rsplit('/',1)[1];calls.append(method)
        return httpx.Response(200,json={'ok':True,'result':{'is_bot':True,'username':'fictional_bot'} if method=='getMe' else {'url':'https://previous.example/webhook'} if method=='getWebhookInfo' else True})
    mock_provider(monkeypatch,handler)
    assert client.post('/api/telegram/connect',json={}).status_code == 409
    assert 'deleteWebhook' not in calls
    result=client.post('/api/telegram/connect',json={'replace_webhook':True}).json()
    assert result['connected'] and not result['enabled'] and result['transport']=='polling'
    assert 'sendMessage' not in calls
    assert client.put('/api/telegram/delivery',json={'authorized':True}).json()['enabled']
    assert os.getenv('MADAR_ALLOW_EXTERNAL_SEND') != 'true'
    assert not client.put('/api/telegram/delivery',json={'authorized':False}).json()['enabled']


def test_authenticated_incoming_updates_are_atomic_and_returning_contacts_match(client,monkeypatch):
    state=demo(client);headers=bind(monkeypatch,state)
    event=update(text='Buy an apartment New Cairo budget 5 million 3 bedrooms')
    assert client.post('/webhooks/telegram',json=event).status_code==401
    assert client.post('/webhooks/telegram',json=event,headers=headers).status_code==200
    assert client.post('/webhooks/telegram',json=event,headers=headers).json()['duplicate']
    client.post('/webhooks/telegram',json=update(2,'budget 6 million'),headers=headers)
    current=client.get('/api/state').json();leads=[l for l in current['leads'] if l['source']=='telegram' and l['external_id']=='101']
    assert len(leads)==1 and leads[0]['budget']==6000000 and leads[0]['location']=='New Cairo'
    assert len([m for m in current['messages'] if m['channel']=='telegram' and m['lead_id']==leads[0]['id']])==4
    assert len([o for o in current['outbox'] if o['channel']=='telegram'])==2
    assert 'Palm Residence' in current['outbox'][-1]['body']
    assert '[Deterministic assistant]' in current['outbox'][-1]['body']
    assert all(o['status']=='Pending' for o in current['outbox'])


@pytest.mark.parametrize('event',[[], {'update_id':'1'}, update(text=''), update(chat=-1), {'update_id':2,'message':{'text':'Hi','chat':{'id':1,'type':'private'},'from':{'id':2}}}])
def test_malformed_updates_fail_safely(client,monkeypatch,event):
    state=demo(client);headers=bind(monkeypatch,state)
    assert client.post('/webhooks/telegram',json=event,headers=headers).status_code==400


def test_fictional_bilingual_booking_requires_two_selections_and_confirmation(client):
    demo(client)
    started=sandbox(client,1,'/start',language='ar')
    assert 'مساعد آلي' in started['reply']
    inquiry=sandbox(client,2,'عايز شقة في التجمع ميزانية خمسة مليون تلات غرف')
    assert 'Palm Residence' in inquiry['reply']
    property_action=inquiry['buttons'][0][0]['callback_data']
    before=len(client.get('/api/state').json()['appointments'])
    slots=sandbox(client,3,callback=property_action)
    selected=sandbox(client,4,callback=slots['buttons'][0][0]['callback_data'])
    assert 'لم يتم الحجز بعد' in selected['reply']
    assert len(client.get('/api/state').json()['appointments'])==before
    confirm=selected['buttons'][0][0]['callback_data']
    other=sandbox(client,5,callback=confirm,chat=202)
    assert not other['buttons']
    booked=sandbox(client,6,callback=confirm)
    assert 'تم تأكيد' in booked['reply']
    sandbox(client,7,callback=confirm)
    assert sandbox(client,6,callback=confirm)['duplicate']
    current=client.get('/api/state').json()
    assert len(current['appointments'])==before+1 and not current['outbox']
    assert 'محجوز' in sandbox(client,8,'/appointments')['reply']


def test_confirmation_rechecks_conflicts_and_inventory(client):
    demo(client)
    offered=sandbox(client,1)
    slots=sandbox(client,2,callback=offered['buttons'][0][0]['callback_data'])
    selected=sandbox(client,3,callback=slots['buttons'][0][0]['callback_data'])
    identifier=selected['buttons'][0][0]['callback_data'].removeprefix('act:')
    with db.connection() as c:
        action=dict(c.execute('SELECT * FROM telegram_actions WHERE id=?',(identifier,)).fetchone());payload=json.loads(action['payload'])
    client.post('/api/appointments',json={'lead_id':action['lead_id'], 'property_id':payload['property_id'], 'agent_id':payload['agent_id'], 'start_at':payload['start_at']}).raise_for_status()
    assert 'no longer available' in sandbox(client,4,callback='act:'+identifier)['reply']


def test_handoff_consent_and_optout_are_shared_with_crm(client):
    demo(client)
    result=sandbox(client,1,'/agent');lead=result['lead_id']
    assert 'human adviser' in result['reply']
    assert not sandbox(client,2,'budget 5 million New Cairo')['reply']
    assert not sandbox(client,3,'/properties')['reply']
    client.post('/api/leads/'+lead+'/handoff',json={'active':False,'reason':'Operator takeover'}).raise_for_status()
    sandbox(client,4,'/subscribe')
    current=client.get('/api/state').json()
    assert next(l for l in current['leads'] if l['id']==lead)['consent']
    sandbox(client,5,'/stop')
    current=client.get('/api/state').json()
    assert next(l for l in current['leads'] if l['id']==lead)['opted_out']
    assert not current['outbox']


def test_polling_leases_durable_offsets_and_official_delivery_without_public_url(client,monkeypatch):
    state=demo(client);bind(monkeypatch,state)
    store({'tenant_id':state['company']['id'],'token':TOKEN,'secret':'fictional','enabled':True,'connected':True,'transport':'polling'})
    calls=[]
    def handler(request):
        method=request.url.path.rsplit('/',1)[1];body=json.loads(request.content);calls.append((method,body))
        return httpx.Response(200,json={'ok':True,'result':[update(50,'Buy apartment New Cairo budget 5 million')] if method=='getUpdates' and body['offset']==0 else [] if method=='getUpdates' else {'message_id':42}})
    mock_provider(monkeypatch,handler)
    assert acquire('123456',state['company']['id'],'one')==0
    assert acquire('123456',state['company']['id'],'two') is None
    asyncio.run(cycle('one'))
    release('one')
    asyncio.run(cycle('two'))
    assert [body['offset'] for method,body in calls if method=='getUpdates']==[0,51]
    sends=[body for method,body in calls if method=='sendMessage']
    assert len(sends)==1 and sends[0]['chat_id']=='101' and 'Palm Residence' in sends[0]['text']
    assert sends[0]['reply_markup']['inline_keyboard']
    assert os.getenv('MADAR_ALLOW_EXTERNAL_SEND') != 'true'
    current=client.get('/api/state').json();assert len([l for l in current['leads'] if l['source']=='telegram' and l['external_id']=='101'])==1


def test_polling_conflict_disables_only_this_bot(client,monkeypatch):
    state=demo(client);bind(monkeypatch,state)
    store({'tenant_id':state['company']['id'],'token':TOKEN,'enabled':True,'connected':True})
    mock_provider(monkeypatch,lambda request:httpx.Response(409,json={'ok':False,'error_code':409}))
    asyncio.run(cycle('one'))
    assert not configuration()['connected'] and not configuration()['enabled']
    with db.connection() as c:
        assert c.execute('SELECT error FROM telegram_polling').fetchone()[0]=='Telegram polling conflict'


def test_telegram_rate_limits_and_uncertain_outcomes_are_not_replayed(client,monkeypatch):
    state=demo(client);headers=bind(monkeypatch,state)
    client.post('/webhooks/telegram',json=update(),headers=headers)
    monkeypatch.setenv('MADAR_ALLOW_TELEGRAM_SEND','true')
    calls=[]
    mock_provider(monkeypatch,lambda request: (calls.append(request) or httpx.Response(429,json={'ok':False,'error_code':429,'parameters':{'retry_after':120}})))
    result=client.post('/api/integrations/dispatch').json();assert result['sent']==0 and len(calls)==1
    current=client.get('/api/state').json();row=current['outbox'][0]
    assert row['status']=='Retry' and datetime.fromisoformat(row['next_attempt']) > datetime.now(timezone.utc)+timedelta(seconds=115)
    assert client.post('/api/integrations/dispatch').json()['sent']==0 and len(calls)==1
    with db.connection() as c:
        c.execute("UPDATE outbox SET next_attempt=? WHERE id=?", (db.now(),row['id']))
        c.execute('DELETE FROM channel_pauses')
    def timeout(request):raise httpx.ReadTimeout('fictional timeout')
    mock_provider(monkeypatch,timeout)
    client.post('/api/integrations/dispatch')
    assert client.get('/api/state').json()['outbox'][0]['status']=='Uncertain'
    client.post('/api/integrations/dispatch')


def test_bot_api_urls_are_redacted_even_in_http_client_logs():
    import logging
    from backend.telegram import TelegramLogFilter
    record=logging.LogRecord('httpx',logging.INFO,'test',1,'HTTP Request: %s',('https://api.telegram.org/bot'+TOKEN+'/getUpdates',),None)
    assert TelegramLogFilter().filter(record)
    assert TOKEN not in record.getMessage() and '[REDACTED]' in record.getMessage()


def test_existing_n8n_reconciliation_drains_only_authorized_telegram(client,monkeypatch):
    state=demo(client);headers=bind(monkeypatch,state)
    monkeypatch.setenv('MADAR_BRIDGE_TOKEN','fictional-bridge')
    client.post('/webhooks/telegram',json=update(),headers=headers)
    calls=[]
    mock_provider(monkeypatch, lambda request: (calls.append(request) or httpx.Response(200,json={'ok':True,'result':{'message_id':99}})))
    bridge={'Authorization':'Bearer fictional-bridge'}
    assert client.post('/api/bridge/reconcile',headers=bridge).status_code==200
    assert not calls
    monkeypatch.setenv('MADAR_ALLOW_TELEGRAM_SEND','true')
    assert client.post('/api/bridge/reconcile',headers=bridge).status_code==200
    assert len(calls)==1 and 'sendMessage' in calls[0].url.path
    assert client.post('/api/bridge/reconcile',headers=bridge).status_code==200 and len(calls)==1


def test_telegram_followups_reuse_consent_and_arabic_language(client):
    demo(client)
    reply=sandbox(client,1,'/start',language='ar');lead=reply['lead_id']
    sandbox(client,2,'/subscribe',language='ar')
    with db.connection() as c:
        c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)", (db.uid(),c.execute('SELECT tenant_id FROM leads WHERE id=?',(lead,)).fetchone()[0],lead,'Fictional follow-up',db.now(),'Pending','followup',db.now()))
    assert client.post('/api/automation/tick').status_code==200
    rows=[o for o in client.get('/api/state').json()['outbox'] if o['lead_id']==lead]
    assert rows and 'مستشارك العقاري' in rows[0]['body']
    sandbox(client,3,'/stop')
    assert all(o['status']=='Held' for o in client.get('/api/state').json()['outbox'] if o['lead_id']==lead)


def test_webhook_registration_requires_https_and_explicit_approval(client,monkeypatch):
    real_admin(client,monkeypatch)
    client.put('/api/telegram/setup',json={'token':TOKEN,'public_origin':'https://telegram.example.com'})
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'ok':True,'result':{'is_bot':True,'username':'fictional'} if request.url.path.endswith('getMe') else True})
    mock_provider(monkeypatch,handler)
    assert client.post('/api/telegram/register-webhook',json={'authorized':True}).status_code==422
    client.post('/api/telegram/test').raise_for_status()
    assert client.post('/api/telegram/register-webhook',json={}).status_code==422
    response=client.post('/api/telegram/register-webhook',json={'authorized':True})
    assert response.status_code==200 and response.json()['registered']
    payload=json.loads(calls[-1].content)
    assert payload['url']=='https://telegram.example.com/webhooks/telegram' and payload['secret_token']
    assert payload['drop_pending_updates'] is False
    assert payload['secret_token'] not in response.text


def test_viewing_inquiry_with_human_request_always_hands_off(client):
    demo(client)
    result=sandbox(client,1,'I need a human adviser for a viewing')
    assert 'human adviser' in result['reply'] and not result['buttons']
    assert not sandbox(client,2,'/properties')['reply']


def test_inflight_verification_cannot_restore_a_revoked_delivery_permission(client,monkeypatch):
    real_admin(client,monkeypatch)
    client.put('/api/telegram/setup',json={'token':TOKEN}).raise_for_status()
    cfg=configuration();cfg.update(enabled=True,verified=True);store(cfg)
    def handler(request):
        newer=configuration();newer['enabled']=False;store(newer)
        return httpx.Response(200,json={'ok':True,'result':{'is_bot':True,'username':'fictional'}})
    mock_provider(monkeypatch,handler)
    assert client.post('/api/telegram/test').status_code==409
    assert configuration()['enabled'] is False
