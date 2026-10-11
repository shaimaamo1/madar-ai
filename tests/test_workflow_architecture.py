import json
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

import httpx

from backend.main import app
from scripts.generate_architecture import catalog
from scripts.n8n_deploy import deploy, workflow_templates

ROOT = Path(__file__).resolve().parent.parent


def test_every_workflow_contract_resolves_to_real_backend_and_modules_are_ordered():
    routes = app.openapi()['paths']
    templates = workflow_templates()
    seen = set()
    assert len(templates) == 14
    for flow in templates:
        assert not flow['active']
        assert flow['settings']['saveDataErrorExecution'] == 'none'
        for node in flow['nodes']:
            parameters = node['parameters']
            if 'url' in parameters:
                endpoint = parameters['url'].replace('http://app:8000', '')
                assert endpoint in routes and 'post' in routes[endpoint]
            reference = parameters.get('workflowId', {})
            if isinstance(reference, dict) and reference.get('value','').startswith('MADAR_WORKFLOW:'):
                assert reference['value'].removeprefix('MADAR_WORKFLOW:') in seen
        seen.add(flow['name'])


def test_diagrams_and_dashboard_catalog_represent_exact_executable_graphs():
    flows = catalog()
    source = (ROOT/'frontend/src/workflowCatalog.ts').read_text()
    generated = json.loads(source.split('export const workflowCatalog = ',1)[1].rstrip().removesuffix(';'))
    assert generated == flows
    for flow in flows:
        tree = ET.parse(ROOT/'docs/diagrams'/ (flow['key']+'.svg'))
        nodes={item.get('data-node-id') for item in tree.iter() if item.get('data-node-id')}
        assert nodes == {n['id'] for n in flow['nodes'] if n['type']!='stickyNote'}
        connections=[item for item in tree.iter() if item.get('marker-end')=='url(#arrow)']
        assert len(connections)==len(flow['edges'])


def test_normalized_event_code_and_sandbox_output_execute_without_network():
    intake=next(w for w in workflow_templates() if w['name']=='MADAR Omnichannel Intake')
    normalize=next(n['parameters']['jsCode'] for n in intake['nodes'] if n['type'].endswith('.code'))
    runner="""const fs=require('fs');const input=JSON.parse(fs.readFileSync(0,'utf8'));const execute=new Function('$input',input.code);const output=execute({all:()=>[{json:input.event}]});process.stdout.write(JSON.stringify(output));"""
    event={'body':{'event_id':'normal-event','lead':{'name':'Fictional visitor','source':'crm','consent':'true'},'text':'New Cairo apartment'}}
    result=subprocess.run(['node','-e',runner],input=json.dumps({'code':normalize,'event':event}),text=True,capture_output=True,check=True)
    data=json.loads(result.stdout)[0]['json']
    assert data['lead']['consent'] is False  # String truthiness must never grant consent.
    assert data['event_id']=='normal-event' and data['text']==event['body']['text']
    failure=subprocess.run(['node','-e',runner],input=json.dumps({'code':normalize,'event':{'body':{'lead':{}}}}),text=True,capture_output=True)
    assert failure.returncode!=0


def test_legacy_four_workflows_recover_and_subworkflow_ids_are_bound(tmp_path):
    legacy=json.loads((ROOT/'scripts/legacy_workflow_identities.json').read_text())
    remote={str(i): {'id':str(i),'name':name,'active':False,'nodes':[{'id':nid,'type':kind} for nid,kind in nodes]} for i,(name,nodes) in enumerate(legacy.items(),1)}
    original_ids={w['name']:w['id'] for w in remote.values()}
    def handler(request):
        path=request.url.path
        if path=='/api/v1/credentials':return httpx.Response(200,json={'id':'test-credential'})
        if request.method=='GET' and path=='/api/v1/workflows':return httpx.Response(200,json={'data':list(remote.values())})
        if request.method=='GET':return httpx.Response(200,json=remote[path.rsplit('/',1)[1]])
        data=json.loads(request.content)
        identifier=path.rsplit('/',1)[1] if request.method=='PUT' else str(len(remote)+1)
        remote[identifier]=dict(data,id=identifier,active=False)
        return httpx.Response(200,json=remote[identifier])
    deploy({'N8N_BASE_URL':'http://localhost:5678','N8N_API_KEY':'test-key','MADAR_BRIDGE_TOKEN':'test-bridge','MADAR_INGEST_TOKEN':'test-ingest'},transport=httpx.MockTransport(handler),state_path=tmp_path/'state.json')
    assert len(remote)==14
    assert all(remote[value]['name']==name for name,value in original_ids.items())
    intelligence=next(w for w in remote.values() if w['name']=='MADAR Lead Intelligence')
    intake=next(w for w in remote.values() if w['name']=='MADAR Omnichannel Intake')
    call=next(n for n in intake['nodes'] if n['type'].endswith('.executeWorkflow'))
    assert call['parameters']['workflowId']['value']==intelligence['id']
    assert not any(w['active'] for w in remote.values())
