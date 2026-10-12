import json
from datetime import datetime
from pathlib import Path

from backend import db
from tests.test_product import client, demo


def test_connected_dataset_counts_relationships_images_and_real_analytics(client):
    state=demo(client)
    assert len(state['properties'])==30 and len(state['leads'])==40
    assert len(state['appointments'])==15 and len(state['tasks'])==20
    assert len([u for u in state['users'] if u['role']=='agent'])==5
    assert len(state['messages'])==100 and len({m['lead_id'] for m in state['messages']})==25
    leads={l['id']:l for l in state['leads']};props={p['id']:p for p in state['properties']};agents={u['id'] for u in state['users']}
    assert {p['property_type'] for p in props.values()}=={'Apartment','Villa','Duplex','Penthouse','Office','Commercial'}
    assert len({p['reference'] for p in props.values()})==30
    for lead in leads.values():
        assert lead['assigned_to'] in agents and lead['external_id'].startswith('sandbox:')
        assert not lead['phone'] and lead['email'].endswith('@demo.invalid')
    for appt in state['appointments']:
        assert appt['lead_id'] in leads and appt['property_id'] in props and appt['agent_id'] in agents
        assert appt['agent_id']==leads[appt['lead_id']]['assigned_to']
        assert datetime.fromisoformat(appt['end_at'])>datetime.fromisoformat(appt['start_at'])
        assert 'DEMO' in appt['notes']
        if appt['status']=='Booked':assert props[appt['property_id']]['status']=='Available'
    for task in state['tasks']:assert task['lead_id'] in leads
    for message in state['messages']:assert message['lead_id'] in leads
    booked=[a for a in state['appointments'] if a['status']=='Booked']
    for a in booked:
        for b in booked:
            if a['id']==b['id']:continue
            if a['agent_id']==b['agent_id'] or a['property_id']==b['property_id']:
                assert a['end_at']<=b['start_at'] or b['end_at']<=a['start_at']
    for prop in props.values():
        assert prop['demo'] and prop['reference'].startswith('DEMO-EG-') and 'FICTIONAL' in prop['description']
        response=client.get(prop['image']);assert response.status_code==200
        assert 'image/webp' in response.headers['content-type']
        assert response.content[:4]==b'RIFF' and response.content[8:12]==b'WEBP'
    metrics=client.get('/api/analytics').json()
    assert metrics['total_leads']==40 and sum(metrics['sources'].values())==40
    assert sum(metrics['pipeline'].values())==40 and sum(metrics['demand_by_area'].values())==40
    assert sum(metrics['appointment_activity'].values())==15
    assert metrics['followups']=={'total':20,'completed':5,'pending':15}
    assert metrics['revenue']==metrics['sales_volume']==0 and metrics['demo']
    assert sum(a['leads'] for a in metrics['agents'])==40
    assert sum(a['appointments'] for a in metrics['agents'])==15
    assert not state['outbox']


def test_load_idempotence_and_seed_reset_preserve_added_records(client):
    before=demo(client)
    assert client.post('/api/demo/load').status_code==200
    assert client.post('/api/demo/load').status_code==200
    after=client.get('/api/state').json()
    for table in ('properties','leads','users','appointments','tasks','messages'):
        assert before[table]==after[table]
    manual=client.post('/api/leads',json={'name':'Added fictional visitor','external_id':'sandbox:added'}).json()['lead']
    referenced=before['leads'][0]
    client.post('/api/leads/'+referenced['id']+'/chat',json={'text':'A new message added during presentation.'}).raise_for_status()
    assert client.post('/api/demo/reset').status_code==200
    reset=client.get('/api/state').json()
    assert any(l['id']==manual['id'] for l in reset['leads'])
    assert any(m['body']=='A new message added during presentation.' for m in reset['messages'])
    assert client.post('/api/demo/load').status_code==200
    again=client.get('/api/state').json()
    for table in ('properties','leads','users','appointments','tasks','messages'):
        assert len(reset[table])==len(again[table])


def test_demo_generation_and_reset_never_mutate_real_workspace_or_telegram(client,monkeypatch):
    assert client.post('/api/auth/login',json={'workspace':'madar','email':'admin@madar.local','password':'TestOnlyPassword123!'}).status_code==200
    real=client.get('/api/state').json()
    lead=client.post('/api/leads',json={'name':'Existing customer','source':'telegram','external_id':'987654321'}).json()['lead']
    prop=client.post('/api/properties',json={'title':'Existing inventory','location':'Maadi','price':2500000,'size':140}).json()
    real=client.get('/api/state').json();pid=next(p['id'] for p in real['properties'] if p['title']=='Existing inventory')
    client.post('/api/appointments',json={'lead_id':lead['id'],'property_id':pid,'agent_id':real['user']['id'],'start_at':'2030-01-01T10:00:00+00:00'}).raise_for_status()
    monkeypatch.setenv('MADAR_INTEGRATION_TENANT_ID',real['company']['id'])
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET','fictional-demo-isolation-secret')
    client.post('/webhooks/telegram',headers={'x-telegram-bot-api-secret-token':'fictional-demo-isolation-secret'},json={'update_id':888,'message':{'text':'Hello','chat':{'id':987654321,'type':'private'}}}).raise_for_status()
    with db.connection() as c:
        snapshot={t:[dict(r) for r in c.execute(f'SELECT * FROM {t} WHERE tenant_id=?',(real['company']['id'],))] for t in ('leads','messages','properties','appointments','outbox','webhook_events','tasks')}
    assert client.post('/api/demo/load').status_code==403
    assert client.post('/api/demo/reset').status_code==403
    import httpx
    def forbidden(*args,**kwargs):raise AssertionError('Demo generation must not call any provider')
    monkeypatch.setattr(httpx,'AsyncClient',forbidden)
    fake=demo(client)
    client.post('/api/demo/load').raise_for_status();client.post('/api/demo/reset').raise_for_status()
    with db.connection() as c:
        for table,rows in snapshot.items():
            assert [dict(r) for r in c.execute(f'SELECT * FROM {table} WHERE tenant_id=?',(real['company']['id'],))]==rows
    assert fake['company']['id']!=real['company']['id']
    assert not client.get('/api/state').json()['outbox']


def test_reset_keeps_added_bookings_and_their_generated_inventory(client):
    state=demo(client)
    property=next(p for p in state['properties'] if p['title']=='Palm Residence')
    lead=client.post('/api/leads',json={'name':'Presentation viewing customer','external_id':'sandbox:presentation-viewing'}).json()['lead']
    appointment=client.post('/api/appointments',json={'lead_id':lead['id'],'property_id':property['id'],'agent_id':state['user']['id'],'start_at':'2030-01-01T10:00:00+00:00'})
    appointment.raise_for_status()
    before=client.get('/api/state').json()
    assert client.post('/api/demo/reset').json()['retained_referenced_demo_records']>=1
    after=client.get('/api/state').json()
    assert next(a for a in after['appointments'] if a['id']==appointment.json()['id'])==next(a for a in before['appointments'] if a['id']==appointment.json()['id'])
    assert next(p for p in after['properties'] if p['id']==property['id'])==property


def test_photographic_manifest_has_30_distinct_optimized_type_matched_assets():
    import hashlib
    from backend.demo_inventory import LISTINGS
    folder=Path(__file__).resolve().parent.parent/'backend/demo_assets'
    manifest=json.loads((folder/'manifest.json').read_text())
    assert len(manifest)==30
    assert len({entry['sha256'] for entry in manifest})==30
    assert len({entry['original_sha256'] for entry in manifest})==30
    for index,(entry,listing) in enumerate(zip(manifest,LISTINGS),1):
        assert entry['reference']==f'DEMO-EG-{index:03}'
        assert entry['title']==listing[0] and entry['property_type']==listing[2]
        assert entry['illustrative'] and not entry['verified_property_photograph']
        assert entry['source']=='Original OpenAI image generation output'
        path=folder/entry['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
        assert path.stat().st_size==entry['bytes'] and 10000<entry['bytes']<300000
        assert entry['width']<=1024 and entry['width']>entry['height']>=600
    assert sum(e['bytes'] for e in manifest)<6_000_000


def test_legacy_svg_urls_display_photos_without_rewriting_existing_records(client):
    state=demo(client)
    tenant=state['company']['id']
    with db.connection() as c:
        for i,prop in enumerate(sorted(state['properties'],key=lambda p:p['reference']),1):
            c.execute('UPDATE properties SET image=?,description=? WHERE tenant_id=? AND id=?',(f'/demo-assets/property-{i:02}.svg','DEMO / FICTIONAL — Original architectural illustration; retained legacy description.',tenant,prop['id']))
        before={table:[dict(row) for row in c.execute(f'SELECT * FROM {table} WHERE tenant_id=? ORDER BY id',(tenant,))] for table in ('properties','leads','appointments','tasks','messages')}
    for i in range(1,31):
        response=client.get(f'/demo-assets/property-{i:02}.svg')
        assert response.status_code==200 and response.headers['content-type']=='image/webp'
        assert response.content[8:12]==b'WEBP'
    assert client.post('/api/demo/load').status_code==200
    client.get('/api/state').raise_for_status()
    client.get('/api/analytics').raise_for_status()
    with db.connection() as c:
        for table,rows in before.items():
            assert [dict(row) for row in c.execute(f'SELECT * FROM {table} WHERE tenant_id=? ORDER BY id',(tenant,))]==rows
    assert client.get('/demo-assets/property-31.svg').status_code==404
