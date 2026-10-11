import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .test_product import client, demo


def test_public_booking_history_and_private_branding(client):
    state = demo(client)
    slug = state['company']['slug']
    chat = client.post('/api/public/chat', json={'tenant_slug': slug, 'text': 'New Cairo apartment budget 5 million 3 bedrooms', 'consent': True}).json()
    payload = {'tenant_slug': slug, 'session': chat['session'], 'property_id': chat['matches'][0]['id']}
    slots = client.post('/api/public/slots', json=payload)
    assert slots.status_code == 200 and slots.json()['slots']
    slot = slots.json()['slots'][0]['start_at']
    assert client.post('/api/public/book', json={**payload, 'start_at': slot}).json()['booked']
    assert client.post('/api/public/book', json={**payload, 'start_at': slot}).status_code == 409
    history = client.post('/api/public/history', json={'tenant_slug': slug, 'session': chat['session']}).json()['messages']
    assert history[0]['direction'] == 'inbound' and history[1]['direction'] == 'outbound'
    assert 'lead_id' not in history[0]
    assert client.post('/api/public/history', json={'tenant_slug': slug, 'session': 'forged'}).status_code == 401
    company = client.get('/api/public/company/' + slug).json()
    assert 'tenant_id' not in company and 'id' not in company
    assert company['timezone'] == state['company']['settings']['timezone']
    assert set(company) == {'company_name','brand_color','logo_url','currency','assistant_name','language','timezone','demo'}


def test_workspace_provisioning_and_password_rotation(client):
    demo(client)
    payload = {'slug': 'client-estates', 'company_name': 'Client Estates', 'owner_name': 'Owner', 'owner_email': 'owner@example.com', 'owner_password': 'ClientInitialPass123!'}
    assert client.post('/api/workspaces', json=payload).status_code == 200
    assert client.post('/api/workspaces', json=payload).status_code == 409
    assert client.post('/api/auth/login', json={'workspace': payload['slug'], 'email': payload['owner_email'], 'password': payload['owner_password']}).status_code == 200
    assert client.get('/api/state').json()['leads'] == []
    assert client.post('/api/demo/reset').status_code == 403
    assert client.post('/api/auth/password', json={'current_password': 'wrong', 'new_password': 'NewOwnerPassword123!'}).status_code == 401
    assert client.post('/api/auth/password', json={'current_password': payload['owner_password'], 'new_password': 'NewOwnerPassword123!'}).status_code == 200
    assert client.post('/api/auth/login', json={'workspace': payload['slug'], 'email': payload['owner_email'], 'password': payload['owner_password']}).status_code == 401


def test_matching_all_constraints_and_human_handoff(client):
    state = demo(client)
    lead = client.post('/api/leads', json={'name': 'Strict requirements', 'budget': 5000000, 'location': 'New Cairo', 'property_type': 'Apartment', 'min_size': 170, 'bedrooms': 3, 'amenities': ['Pool'], 'intent': 'buy'}).json()['lead']
    matches = client.get('/api/leads/' + lead['id'] + '/matches').json()
    assert [p['title'] for p in matches] == ['Palm Residence']
    assert client.patch('/api/leads/' + lead['id'], json={'budget': 1000000}).status_code == 200
    assert client.get('/api/leads/' + lead['id'] + '/matches').json() == []
    result = client.post('/api/leads/' + lead['id'] + '/chat', json={'text': 'I need a human for a legal question'}).json()
    assert 'human adviser' in result['reply']
    assert any(t['kind'] == 'handoff' for t in client.get('/api/state').json()['tasks'])


def test_workflow_definitions_have_safe_defaults():
    paths = list(Path('workflows').glob('*.json'))
    assert len(paths) == 14
    for path in paths:
        wf = json.loads(path.read_text())
        assert wf['active'] is False
        names = {n['name'] for n in wf['nodes']}
        assert len(names) == len(wf['nodes'])
        for name, edges in wf['connections'].items():
            assert name in names
            for branch in edges['main']:
                for edge in branch:
                    assert edge['node'] in names
        for node in wf['nodes']:
            if node['type'] == 'n8n-nodes-base.httpRequest':
                assert node['credentials']['httpHeaderAuth']['name'].startswith('MADAR')
                assert node['parameters']['url'].startswith('http://app:8000/')
                assert node['retryOnFail'] and node['maxTries'] == 3
                assert 'Authorization' not in json.dumps(node['parameters'])


def test_website_form_does_not_grant_access_to_existing_contacts(client):
    state = demo(client)
    lead = state['leads'][0]
    response = client.post('/api/public/lead', json={'tenant_slug': state['company']['slug'], 'lead': {'name': 'Unverified caller', 'email': lead['email']}})
    assert response.status_code == 200 and response.json() == {'received': True}
    fresh = client.post('/api/public/lead', json={'tenant_slug': state['company']['slug'], 'lead': {'name': 'New form visitor', 'email': 'fresh@example.com'}})
    assert fresh.json() == {'received': True}


def test_model_interpretation_uses_source_quotes_and_never_model_property_claims(client, monkeypatch):
    import httpx
    import backend.assistant as assistant
    state = demo(client)
    monkeypatch.setenv('MADAR_AI_API_KEY', 'test-only-placeholder')
    monkeypatch.setenv('MADAR_ALLOW_MODEL_USAGE', 'true')
    class FakeModel:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            interpretation = {'preferences': [{'field': 'budget', 'value': 5000000, 'quote': 'five million', 'confidence': .95}, {'field': 'location', 'value': 'New Cairo', 'quote': 'Cairo east', 'confidence': .95}, {'field': 'bedrooms', 'value': 3, 'quote': 'invented quote', 'confidence': 1}]}
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(interpretation)}}]}, request=httpx.Request('POST', 'https://api.openai.com/v1/chat/completions'))
    monkeypatch.setattr(assistant.httpx, 'AsyncClient', FakeModel)
    created = client.post('/api/leads', json={'name': 'Model test'}).json()['lead']
    reply = client.post('/api/leads/' + created['id'] + '/chat', json={'text': 'My budget is five million around Cairo east.'})
    assert reply.status_code == 200, reply.text
    result = reply.json()
    assert result['mode'] == 'model-assisted' and result['lead']['budget'] == 5000000
    assert result['lead']['bedrooms'] == 0
    assert 'Palm Residence' in result['reply'] and '4,800,000' in result['reply']


def test_approved_dispatch_uses_official_api_and_tracks_delivery(client, monkeypatch):
    import httpx
    import backend.integrations as integrations
    state = demo(client)
    monkeypatch.setenv('MADAR_INTEGRATION_TENANT_ID', state['company']['id'])
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', 'test-webhook')
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'test-only-bot')
    event = {'update_id': 800, 'message': {'text': 'Hello', 'chat': {'id': 42, 'type': 'private'}}}
    assert client.post('/webhooks/telegram', json=event, headers={'x-telegram-bot-api-secret-token': 'test-webhook'}).status_code == 200
    calls = []
    class FakeProvider:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            calls.append((url, kwargs['json']))
            return httpx.Response(200, json={'ok': True, 'result': {'message_id': 990}})
    monkeypatch.setattr(integrations.httpx, 'AsyncClient', FakeProvider)
    assert client.post('/api/integrations/dispatch').json()['sent'] == 0
    assert calls == []
    monkeypatch.setenv('MADAR_ALLOW_EXTERNAL_SEND', 'true')
    assert client.post('/api/integrations/dispatch').json()['sent'] == 1
    assert calls[0][0].startswith('https://api.telegram.org/')
    outbox = client.get('/api/state').json()['outbox'][0]
    assert outbox['status'] == 'Sent' and outbox['external_id'] == '990'
    assert client.post('/api/integrations/dispatch').json()['sent'] == 0
