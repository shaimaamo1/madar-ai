import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import db, security
from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.sqlite3')
    monkeypatch.setenv('MADAR_ADMIN_PASSWORD', 'TestOnlyPassword123!')
    monkeypatch.delenv('MADAR_AI_API_KEY', raising=False)
    monkeypatch.delenv('MADAR_ALLOW_EXTERNAL_SEND', raising=False)
    security._rates.clear()
    with TestClient(app) as c:
        yield c


def demo(client):
    assert client.post('/api/auth/demo').status_code == 200
    return client.get('/api/state').json()


def test_complete_customer_journey(client):
    state = demo(client)
    slug = state['company']['slug']
    response = client.post('/api/public/chat', json={'tenant_slug': slug, 'name': 'Journey customer', 'consent': True, 'text': 'I want to buy an apartment in New Cairo, budget 5 million, 3 bedrooms'})
    assert response.status_code == 200, response.text
    chat = response.json()
    assert chat['matches'][0]['title'] == 'Palm Residence'
    assert chat['mode'] == 'rules'
    assert 'lead' not in chat
    state = client.get('/api/state').json()
    lead = next(l for l in state['leads'] if l['name'] == 'Journey customer')
    assert lead['stage'] == 'Qualified' and lead['budget'] == 5000000
    # Tomorrow 10 UTC falls within Cairo business hours.
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    booking = {'lead_id': lead['id'], 'property_id': chat['matches'][0]['id'], 'agent_id': lead['assigned_to'], 'start_at': start}
    result = client.post('/api/appointments', json=booking)
    assert result.status_code == 200, result.text
    appointment = result.json()['id']
    assert client.post('/api/appointments', json=booking).status_code == 409
    assert client.patch(f'/api/appointments/{appointment}/Completed').status_code == 200
    tick = client.post('/api/automation/tick')
    assert tick.status_code == 200 and tick.json()['queued'] >= 1
    assert client.post('/api/automation/tick').json()['queued'] == 0
    assert client.post('/api/integrations/dispatch').json()['sent'] == 0
    assert client.post('/api/deals', json={'lead_id': lead['id'], 'property_id': chat['matches'][0]['id'], 'amount': 4800000, 'commission': 96000, 'status': 'Won'}).status_code == 200
    analytics = client.get('/api/analytics').json()
    assert analytics['total_leads'] == 7 and analytics['revenue'] == 192000
    assert analytics['average_response_seconds'] is not None


def test_tenant_isolation_and_public_sessions(client):
    first = demo(client)
    lead = first['leads'][0]
    prop = first['properties'][0]
    second = demo(client)
    assert second['company']['id'] != first['company']['id']
    assert client.patch('/api/leads/' + lead['id'], json={'stage': 'Won'}).status_code == 404
    assert client.get('/api/leads/' + lead['id'] + '/matches').status_code == 404
    assert client.post('/api/appointments', json={'lead_id': second['leads'][0]['id'], 'property_id': prop['id'], 'agent_id': second['users'][0]['id'], 'start_at': '2030-01-01T10:00:00Z'}).status_code == 404
    assert client.post('/api/public/chat', json={'tenant_slug': first['company']['slug'], 'session': 'forged', 'text': 'hello'}).status_code == 401


def test_deduplication_and_contact_conflict(client):
    demo(client)
    payload = {'name': 'New lead', 'phone': '+20 123-456', 'email': 'Person@Example.com'}
    first = client.post('/api/leads', json=payload).json()
    second = client.post('/api/leads', json=payload).json()
    assert first['created'] and not second['created']
    assert first['lead']['id'] == second['lead']['id']
    assert client.post('/api/leads', json={'name': 'Other', 'email': 'other@example.com'}).status_code == 200
    assert client.post('/api/leads', json={**payload, 'email': 'other@example.com'}).status_code == 409


def test_arabic_qualification_optout_and_inventory(client):
    state = demo(client)
    lead = state['leads'][0]
    reply = client.post('/api/leads/' + lead['id'] + '/chat', json={'text': 'عايز شقة في التجمع ميزانيتي ٥ مليون و٣ غرف'})
    assert reply.status_code == 200, reply.text
    assert reply.json()['lead']['location'] == 'New Cairo'
    assert reply.json()['matches'][0]['title'] == 'Palm Residence'
    stopped = client.post('/api/leads/' + lead['id'] + '/chat', json={'text': 'وقف الرسائل'}).json()
    assert stopped['lead']['opted_out'] and not stopped['lead']['consent']
    with db.connection() as c:
        c.execute("UPDATE tasks SET due_at='2000-01-01T00:00:00+00:00' WHERE tenant_id=? AND lead_id=?", (state['company']['id'], lead['id']))
    client.post('/api/automation/tick')
    assert not any(o['lead_id'] == lead['id'] for o in client.get('/api/state').json()['outbox'])


def test_auth_roles_csrf_and_unknown_fields(client):
    assert client.get('/api/state').status_code == 401
    assert client.post('/api/auth/login', json={'email': 'admin@madar.local', 'password': 'wrong'}).status_code == 401
    state = demo(client)
    assert client.post('/api/leads', json={'name': 'X', 'tenant_id': 'forged'}).status_code == 422
    assert client.post('/api/leads', headers={'Origin': 'https://evil.invalid'}, json={'name': 'X'}).status_code == 403
    assert client.post('/api/users', json={'email': 'agent@example.com', 'name': 'Sales agent', 'password': 'AgentPassword123!', 'role': 'agent'}).status_code == 200
    assert client.post('/api/auth/login', json={'workspace': state['company']['slug'], 'email': 'agent@example.com', 'password': 'AgentPassword123!'}).status_code == 200
    assert client.put('/api/settings', json=state['company']['settings']).status_code == 403
    assert client.post('/api/users', json={'email': 'x@example.com', 'name': 'X', 'password': 'AnotherPassword123!'}).status_code == 403


def test_webhook_signatures_and_idempotency(client, monkeypatch):
    state = demo(client)
    monkeypatch.setenv('MADAR_INTEGRATION_TENANT_ID', state['company']['id'])
    monkeypatch.setenv('META_APP_SECRET', 'local-test-secret')
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', 'telegram-test')
    body = json.dumps({'entry': [{'changes': [{'value': {'messages': [{'id': 'wa-test', 'from': '201000000000', 'type': 'text', 'text': {'body': 'budget 5 million New Cairo'}}]}}]}]}).encode()
    assert client.post('/webhooks/meta', content=body).status_code == 401
    signature = 'sha256=' + hmac.new(b'local-test-secret', body, hashlib.sha256).hexdigest()
    for _ in range(2):
        assert client.post('/webhooks/meta', content=body, headers={'x-hub-signature-256': signature}).status_code == 200
    result = client.get('/api/state').json()
    assert len([m for m in result['messages'] if m['external_id'] == 'wa-test']) == 1
    assert len(result['outbox']) == 1
    tg = {'update_id': 1, 'message': {'text': 'hello', 'chat': {'id': 123, 'type': 'private'}, 'from': {'first_name': 'TG'}}}
    assert client.post('/webhooks/telegram', json=tg).status_code == 401
    assert client.post('/webhooks/telegram', json=tg, headers={'x-telegram-bot-api-secret-token': 'telegram-test'}).status_code == 200
    assert client.post('/webhooks/telegram', json=tg, headers={'x-telegram-bot-api-secret-token': 'telegram-test'}).json()['duplicate']


def test_reschedule_and_business_hours(client):
    state = demo(client)
    booking = {'lead_id': state['leads'][0]['id'], 'property_id': state['properties'][0]['id'], 'agent_id': state['users'][0]['id'], 'start_at': '2030-01-01T10:00:00Z'}
    first = client.post('/api/appointments', json=booking).json()
    assert client.put('/api/appointments/' + first['id'], json={**booking, 'start_at': '2030-01-02T10:00:00Z'}).status_code == 200
    assert client.post('/api/appointments', json={**booking, 'start_at': '2030-01-01T01:00:00Z'}).status_code == 422
    assert client.patch('/api/appointments/' + first['id'] + '/Cancelled').status_code == 200


def test_demo_reset_preserves_other_tenants(client):
    first = demo(client)
    second = demo(client)
    client.post('/api/leads', json={'name': 'Temporary'})
    assert client.post('/api/demo/reset').status_code == 200
    assert len(client.get('/api/state').json()['leads']) == 6
    with db.connection() as c:
        assert c.execute('SELECT COUNT(*) FROM leads WHERE tenant_id=?', (first['company']['id'],)).fetchone()[0] == 6


def test_bridge_and_settings_validation(client, monkeypatch):
    state = demo(client)
    monkeypatch.setenv('MADAR_INTEGRATION_TENANT_ID', state['company']['id'])
    monkeypatch.setenv('MADAR_BRIDGE_TOKEN', 'local-bridge')
    assert client.post('/api/bridge/tick').status_code == 401
    assert client.post('/api/bridge/tick', headers={'Authorization': 'Bearer local-bridge'}).status_code == 200
    cfg = state['company']['settings']
    assert client.put('/api/settings', json={**cfg, 'timezone': 'invalid'}).status_code == 422
    assert client.put('/api/settings', json={**cfg, 'company_name': 'Custom Estates', 'currency': 'AED'}).status_code == 200
    assert client.get('/api/state').json()['company']['name'] == 'Custom Estates'
