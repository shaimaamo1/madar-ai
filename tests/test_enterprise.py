import json
from datetime import datetime, timedelta, timezone

import pytest
from backend import db
from tests.test_product import client, demo
from tests.test_premium_operations import bind


def queued(client, monkeypatch):
    state=demo(client)
    headers=bind(monkeypatch,state)
    run=client.post('/api/demo/runs').json()
    claimed=client.post('/api/bridge/demo/claim',headers=headers).json()
    assert claimed['run_id']==run['id'] and 'run_token' not in run
    return state,headers,claimed


def advance(client,headers,claimed,kind):
    allowed={k:v for k,v in claimed.items() if k in ('run_id','run_token','event_id','lead_id')}
    envelope=dict(allowed,kind=kind)
    context=client.post('/api/bridge/enterprise/context',headers=headers,json=envelope)
    assert context.status_code==200,context.text
    result=client.post('/api/bridge/enterprise/commit',headers=headers,json=dict(envelope,execution_id='fixture-execution',analysis={'test':True}))
    assert result.status_code==200,result.text
    return result.json(),envelope


def test_full_demo_creates_real_records_without_claiming_n8n_verification(client,monkeypatch):
    state,headers,claimed=queued(client,monkeypatch)
    from backend.enterprise import KINDS
    for kind in KINDS:
        result,envelope=advance(client,headers,claimed,kind)
        replay=client.post('/api/bridge/enterprise/commit',headers=headers,json=dict(envelope,execution_id='another-fixture',analysis={})).json()
        assert replay['duplicate']
        claimed.update(lead_id=result['lead_id'])
    finish=client.post('/api/bridge/demo/complete',headers=headers,json={'run_id':claimed['run_id'],'run_token':claimed['run_token'],'execution_id':'fixture-full-demo'})
    assert finish.status_code==200 and finish.json()['status']=='Awaiting verification'
    monkeypatch.setenv('N8N_ENABLED','false')
    assert client.post('/api/demo/runs/'+claimed['run_id']+'/verify').json()['status']=='Awaiting verification'
    current=client.get('/api/state').json()
    assert len(current['leads'])==len(state['leads'])+1
    assert len(current['appointments'])==len(state['appointments'])+1
    assert current['outbox']==[] or all(o['status']!='Sent' for o in current['outbox'])
    assert len(client.get('/api/enterprise/artifacts').json())==8
    runs=client.get('/api/demo/runs').json()
    assert len(runs[0]['steps'])==8 and 'capability_hash' not in json.dumps(runs)
    assert client.post('/api/bridge/enterprise/context',headers=headers,json=dict(envelope)).status_code==403


def test_demo_capabilities_reject_cross_tenant_injection_and_wrong_order(client,monkeypatch):
    state,headers,claim=queued(client,monkeypatch)
    base=dict(claim,kind='intake')
    assert client.post('/api/bridge/enterprise/context',headers=headers,json={**base,'lead_id':state['leads'][0]['id']}).status_code==403
    assert client.post('/api/bridge/enterprise/context',headers=headers,json={**base,'text':'untrusted scenario override'}).status_code==403
    assert client.post('/api/bridge/enterprise/context',headers=headers,json={**base,'run_token':'bad'}).status_code==403
    assert client.post('/api/bridge/enterprise/context',headers=headers,json={**base,'event_id':'wrong-run'}).status_code==403
    assert client.post('/api/bridge/enterprise/commit',headers=headers,json={**base,'kind':'reporting'}).status_code==409
    second=demo(client)
    assert client.get('/api/demo/runs').json()==[]
    assert client.get('/api/enterprise/artifacts').json()==[]
    assert client.post('/api/demo/runs/'+claim['run_id']+'/verify').status_code==404


def test_health_is_truthful_and_does_not_return_credentials(client,monkeypatch):
    demo(client)
    monkeypatch.setenv('N8N_ENABLED','false')
    monkeypatch.setenv('N8N_API_KEY','fixture-private-key')
    result=client.get('/api/system-health')
    assert result.status_code==200 and 'fixture-private-key' not in result.text
    checks={x['component']:x for x in result.json()['checks']}
    assert checks['Backend']['status']==checks['Database']['status']=='PASS'
    assert checks['n8n API']['status']==checks['Windows execution']['status']=='NOT VERIFIED'


def test_five_agents_are_grounded_and_sandbox_never_calls_paid_provider(client,monkeypatch):
    state=demo(client)
    import backend.ai_agents as agents
    async def forbidden(*args,**kwargs):
        raise AssertionError('Paid model must not run for a fictional tenant')
    monkeypatch.setattr(agents,'interpret',forbidden)
    monkeypatch.setenv('MADAR_AI_API_KEY','fictional')
    monkeypatch.setenv('MADAR_ALLOW_MODEL_USAGE','true')
    response=client.post('/api/leads/'+state['leads'][0]['id']+'/agents',json={'language':'ar'})
    assert response.status_code==200
    result=response.json()
    assert len(result)==5 and all(v['mode']=='deterministic' and not v['provider_called'] for v in result.values())
    assert result['reply_drafting']['sent'] is False
    ids={p['id'] for p in state['properties']}
    assert set(result['reply_drafting']['property_ids'])<=ids


def test_migration_is_additive_and_demo_reset_cannot_affect_another_tenant(client,monkeypatch):
    first,headers,claimed=queued(client,monkeypatch)
    advance(client,headers,claimed,'intake')
    second=demo(client)
    before=len(second['leads'])
    db.migrate();db.migrate()
    assert len(client.get('/api/state').json()['leads'])==before
    assert client.post('/api/demo/reset').status_code==200
    with db.connection() as c:
        assert c.execute('SELECT COUNT(*) FROM enterprise_artifacts WHERE tenant_id=?',(first['company']['id'],)).fetchone()[0]==1


def test_every_enterprise_code_stage_executes_against_real_backend_context(client,monkeypatch):
    import subprocess
    from scripts.enterprise_stages import STAGES
    from scripts.n8n_deploy import workflow_templates
    state,headers,claimed=queued(client,monkeypatch)
    runner="""const fs=require('fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));let context=x.context;for(const code of x.codes){const result=new Function('$input',code)({all:()=>[{json:context}]});context=result[0].json;}process.stdout.write(JSON.stringify(context.analysis));"""
    for kind in STAGES:
        envelope={k:v for k,v in claimed.items() if k in ('run_id','run_token','event_id','lead_id')};envelope['kind']=kind
        context=client.post('/api/bridge/enterprise/context',headers=headers,json=envelope).json()
        from scripts.enterprise_stages import NAMES
        flow=next(f for f in workflow_templates() if f['name']==NAMES[kind])
        names={x[0] for x in STAGES[kind]}
        codes=[n['parameters']['jsCode'] for n in flow['nodes'] if n['name'] in names]
        result=subprocess.run(['node','-e',runner],input=json.dumps({'context':context,'codes':codes}),text=True,capture_output=True,check=True)
        analysis=json.loads(result.stdout)
        assert len(analysis)==16
        for stage in STAGES[kind]:
            if len(stage)>3:
                assert analysis[stage[1]] is True,(kind,stage[0])
        output=client.post('/api/bridge/enterprise/commit',headers=headers,json=dict(envelope,analysis=analysis)).json()
        assert 'lead_id' in output,output
        claimed['lead_id']=output['lead_id']


def test_model_intent_adapter_rejects_unquoted_output_and_retries_only_transient_failures(monkeypatch):
    import asyncio
    import httpx
    from backend.ai_agents import interpret
    monkeypatch.setenv('MADAR_AI_API_KEY','fictional-provider-fixture')
    responses=[httpx.Response(503),httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'intent':'viewing','readiness':'viewing_ready','urgency':'normal','quote':'viewing','confidence':.95})}}],'usage':{'total_tokens':30}})]
    calls=[]
    def handler(request):
        calls.append(request)
        return responses.pop(0)
    real=httpx.AsyncClient
    monkeypatch.setattr('backend.ai_agents.httpx.AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handler),**kwargs))
    result,usage=asyncio.run(interpret('Can I arrange a viewing?'))
    assert result['intent']=='viewing' and len(calls)==2 and usage['total_tokens']==30
    responses.append(httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'intent':'followup_consent','readiness':'qualified','urgency':'normal','quote':'fabricated permission','confidence':.99})}}]}))
    with pytest.raises(ValueError):asyncio.run(interpret('Can I arrange a viewing?'))


def test_previous_export_identities_are_recoverable_without_a_manifest(tmp_path):
    import httpx
    from scripts.n8n_deploy import deploy, ROOT
    old=json.loads((ROOT/'scripts/workflow_identity_versions.json').read_text())
    remote={str(i):{'id':str(i),'name':name,'active':False,'nodes':[{'id':x,'type':y} for x,y in versions[0]['nodes']]} for i,(name,versions) in enumerate(old.items(),1)}
    original={w['name']:w['id'] for w in remote.values()}
    def handler(request):
        path=request.url.path
        if path=='/api/v1/credentials':return httpx.Response(200,json={'id':'fictional-credential'})
        if request.method=='GET' and path=='/api/v1/workflows':return httpx.Response(200,json={'data':list(remote.values())})
        if request.method=='GET':return httpx.Response(200,json=remote[path.rsplit('/',1)[1]])
        data=json.loads(request.content);identifier=path.rsplit('/',1)[1] if request.method=='PUT' else str(len(remote)+1)
        remote[identifier]=dict(data,id=identifier,active=False)
        return httpx.Response(200,json=remote[identifier])
    deploy({'N8N_BASE_URL':'http://localhost:5678','N8N_API_KEY':'fictional','MADAR_BRIDGE_TOKEN':'fictional','MADAR_INGEST_TOKEN':'fictional'},transport=httpx.MockTransport(handler),state_path=tmp_path/'manifest.json')
    assert len(remote)==14 and all(remote[value]['name']==name for name,value in original.items())
    deploy({'N8N_BASE_URL':'http://localhost:5678','N8N_API_KEY':'fictional','MADAR_BRIDGE_TOKEN':'fictional','MADAR_INGEST_TOKEN':'fictional'},transport=httpx.MockTransport(handler),state_path=tmp_path/'manifest.json')
    assert len(remote)==14 and not any(w['active'] for w in remote.values())


def test_scoped_failures_revoke_demo_capabilities_and_leave_redacted_evidence(client,monkeypatch):
    state,headers,claimed=queued(client,monkeypatch)
    envelope=dict(claimed,kind='intake',execution_id='fixture-failed',reason='validation_failed')
    assert client.post('/api/bridge/enterprise/failure',headers=headers,json=envelope).json()['status']=='Failed'
    assert client.get('/api/demo/runs').json()[0]['status']=='Failed'
    incident=client.get('/api/state').json()['incidents'][0]
    assert incident['category']=='workflow_failure' and claimed['run_token'] not in json.dumps(incident)
    assert client.post('/api/bridge/enterprise/context',headers=headers,json=claimed).status_code==403
    assert client.post('/api/demo/runs').json()['id']!=claimed['run_id']


def test_verification_never_accepts_an_old_or_unrelated_n8n_execution(client,monkeypatch):
    state,headers,claimed=queued(client,monkeypatch)
    with db.connection() as c:
        c.execute("UPDATE demo_runs SET status='Awaiting verification',execution_id='123' WHERE id=?",(claimed['run_id'],))
    import backend.enterprise as enterprise
    async def old_execution(path):
        return {'status':'success','finished':True,'workflowId':'fictional','startedAt':'2020-01-01T00:00:00Z'} if path.startswith('executions') else {'name':'MADAR Full Demo'}
    monkeypatch.setattr(enterprise,'n8n_read',old_execution)
    assert client.post('/api/demo/runs/'+claimed['run_id']+'/verify').json()['status']=='Awaiting verification'


def test_intake_shares_existing_webhook_receipts_and_preserves_queue_behavior(client,monkeypatch):
    state=demo(client);headers=bind(monkeypatch,state)
    monkeypatch.setenv('MADAR_INGEST_TOKEN','fictional-ingest')
    body={'event_id':'shared-event','lead':{'name':'Existing integration customer','source':'whatsapp','external_id':'sandbox:old-contract','consent':True},'text':'New Cairo apartment 5 million 3 bedrooms'}
    original=client.post('/api/integrations/ingest',headers={'Authorization':'Bearer fictional-ingest'},json=body)
    assert original.status_code==200
    before=client.get('/api/state').json()
    replay=client.post('/api/bridge/enterprise/commit',headers=headers,json=dict(body,kind='intake'))
    assert replay.status_code==200 and replay.json()['duplicate']
    assert replay.json()['lead_id']==original.json()['lead_id']
    after=client.get('/api/state').json()
    assert len(after['messages'])==len(before['messages']) and len(after['leads'])==len(before['leads']) and len(after['outbox'])==len(before['outbox'])
    body['event_id']='new-event'
    fresh=client.post('/api/bridge/enterprise/commit',headers=headers,json=dict(body,kind='intake'))
    assert fresh.status_code==200 and not fresh.json()['duplicate']
    again=client.post('/api/integrations/ingest',headers={'Authorization':'Bearer fictional-ingest'},json=body)
    assert again.status_code==200 and again.json()['duplicate']
    assert len(client.get('/api/state').json()['outbox'])==len(before['outbox'])+1
