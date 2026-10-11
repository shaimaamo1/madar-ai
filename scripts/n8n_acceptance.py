"""Opt-in developer acceptance against an isolated disposable Cloud/Linux fixture.

Never reads .env, connects to the owner's laptop, activates exports, or mounts
customer data. Requires an already-cached Docker image and Python test environment.
This is NOT part of Windows startup and adds no host dependency there.
"""
import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

from scripts.n8n_deploy import deploy, workflow_templates

ROOT = Path(__file__).resolve().parent.parent
IMAGE = 'n8nio/n8n:1.113.3'


def acceptance(output, screenshots=False):
    report={'runtime':IMAGE,'fixture':'Disposable isolated Cloud/Linux Docker, fictional data only','windows':'NOT VERIFIED','owner_local_n8n':'NOT VERIFIED','provider_delivery':'NOT VERIFIED','checks':[]}
    name='madar-acceptance-'+secrets.token_hex(6)
    docker_env={k:v for k,v in os.environ.items() if k in ('PATH','DOCKER_HOST','DOCKER_CONFIG','LANG','TMPDIR')}
    def docker(*args, timeout=120):
        result=subprocess.run(['docker',*args],env=docker_env,capture_output=True,text=True,timeout=timeout)
        if result.returncode:
            category=next((m for m in ('Invalid output format','No start node','No permission','403','404','Extra inputs') if m in result.stdout+result.stderr),'unclassified runtime error')
            raise RuntimeError('Docker acceptance failed: '+category+'; payload omitted')
        return result.stdout.strip()
    docker('image','inspect',IMAGE)  # No implicit pull, new service or paid request.
    with tempfile.TemporaryDirectory(prefix='madar-n8n-acceptance-') as directory:
        private=Path(directory);server=None
        try:
            docker('run','-d','--name',name,'-p','127.0.0.1::5678','--add-host','host.docker.internal:host-gateway','-e','N8N_SECURE_COOKIE=false','-e','N8N_DIAGNOSTICS_ENABLED=false','-e','N8N_VERSION_NOTIFICATIONS_ENABLED=false','-e','N8N_TEMPLATES_ENABLED=false','-e','N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true','-e','N8N_RUNNERS_ENABLED=false',IMAGE)
            address=docker('port',name,'5678/tcp')
            if not address.startswith('127.0.0.1:'):raise RuntimeError('Fixture port must remain loopback only')
            base='http://'+address
            with httpx.Client(base_url=base,timeout=30,trust_env=False) as n8n:
                for _ in range(150):
                    try:
                        ready=n8n.get('/rest/settings')
                        if ready.status_code==200 and 'application/json' in ready.headers.get('content-type','') and isinstance(ready.json().get('data'),dict):break
                    except httpx.HTTPError:pass
                    time.sleep(.2)
                else:raise RuntimeError('Isolated n8n did not start')
                password=secrets.token_urlsafe(24)+'Aa1!'
                setup=n8n.post('/rest/owner/setup',json={'email':'fixture@example.invalid','firstName':'Fixture','lastName':'Owner','password':password})
                setup.raise_for_status()
                login=n8n.post('/rest/login',json={'emailOrLdapLoginId':'fixture@example.invalid','password':password});login.raise_for_status()
                response=n8n.post('/rest/api-keys',json={'label':'disposable-acceptance','expiresAt':int(time.time())+3600,'scopes':['workflow:read','workflow:create','workflow:update','credential:create','execution:read']});response.raise_for_status()
                key=response.json()['data']['rawApiKey']
                with socket.socket() as port_socket:
                    port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1]
                local='http://127.0.0.1:'+str(port)
                bridge=secrets.token_urlsafe(32);ingest=secrets.token_urlsafe(32)
                env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','PYTHONPATH')}
                env.update(MADAR_DB_PATH=str(private/'app.sqlite3'),MADAR_PUBLIC_URL=local,MADAR_ADMIN_PASSWORD=password,MADAR_ENV='development',MADAR_DEMO_MODE='true',MADAR_ALLOW_EXTERNAL_SEND='false',MADAR_ALLOW_MODEL_USAGE='false',N8N_ENABLED='true',N8N_CONTAINER_URL=base,N8N_BASE_URL=base,N8N_API_KEY=key,MADAR_BRIDGE_TOKEN=bridge,MADAR_INGEST_TOKEN=ingest,MADAR_INTEGRATION_WORKSPACE='madar')
                with (private/'app.log').open('w') as logs:
                    server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','0.0.0.0','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=logs,stderr=subprocess.STDOUT)
                with httpx.Client(base_url=local,headers={'Origin':local},timeout=30,trust_env=False) as app:
                    for _ in range(100):
                        try:
                            if app.get('/api/health').status_code==200:break
                        except httpx.HTTPError:pass
                        time.sleep(.1)
                    else:raise RuntimeError('Fictional MADAR backend did not start')
                    settings={'N8N_BASE_URL':base,'N8N_API_KEY':key,'MADAR_BRIDGE_TOKEN':bridge,'MADAR_INGEST_TOKEN':ingest,'MADAR_N8N_APP_URL':'http://host.docker.internal:'+str(port)}
                    manifest=private/'manifest.json'
                    deploy(settings,state_path=manifest);before=json.loads(manifest.read_text())
                    deploy(settings,state_path=manifest);after=json.loads(manifest.read_text())
                    assert before==after and len(after['workflows'])==14
                    report['checks'].append({'component':'Actual API import and repeat import','status':'PASS','workflow_count':14})
                    for flow in workflow_templates():
                        stored=n8n.get('/api/v1/workflows/'+str(after['workflows'][flow['name']]),headers={'X-N8N-API-KEY':key})
                        stored.raise_for_status();current=stored.json()
                        assert [(n['id'],n['position']) for n in current['nodes']]==[(n['id'],n['position']) for n in flow['nodes']]
                        assert current['connections']==flow['connections'] and not current['active']
                        assert not any(n['type'].endswith('.stickyNote') for n in current['nodes'])
                    report['checks'].append({'component':'Stored clean layouts and unchanged connections for all 14 workflows','status':'PASS','executable_nodes':327})
                    app.post('/api/auth/demo').raise_for_status()
                    run=app.post('/api/demo/runs');run.raise_for_status();run_id=run.json()['id']
                    print('Executing actual Full Demo',flush=True)
                    docker('exec',name,'n8n','execute','--id='+str(after['workflows']['MADAR Full Demo']))
                    print('Actual Full Demo CLI returned success',flush=True)
                    runs=app.get('/api/demo/runs').json();assert runs[0]['id']==run_id and len(runs[0]['steps'])==8
                    result=app.post('/api/demo/runs/'+run_id+'/verify');result.raise_for_status();print('Backend verification status:',result.json().get('status'),flush=True);assert result.json()['status']=='Verified'
                    remote=n8n.get('/api/v1/executions/'+runs[0]['execution_id']+'?includeData=false',headers={'X-N8N-API-KEY':key});remote.raise_for_status();execution=remote.json()
                    assert execution['status']=='success' and execution['finished']
                    report['checks'].append({'component':'Actual Full Demo plus eight business modules','status':'PASS','execution_id':execution['id'],'workflow_id':execution['workflowId'],'steps':[{k:s[k] for k in ('kind','execution_id')} for s in runs[0]['steps']]})
                    state=app.get('/api/state').json();artifacts=app.get('/api/enterprise/artifacts').json()
                    assert len(artifacts)==8 and len([l for l in state['leads'] if l['external_id'].startswith('sandbox:demo:')])==1
                    appointment=next(x['result']['appointment'] for x in artifacts if x['kind']=='appointment')
                    booking={k:appointment[k] for k in ('lead_id','property_id','agent_id','start_at')}
                    assert app.post('/api/appointments',json=booking).status_code==409
                    assert not any(o['status']=='Sent' for o in state['outbox'])
                    assert all(x['result']['external_messages_sent']==0 for x in artifacts)
                    assert not any('run_token' in x['result'] for x in artifacts)
                    report['checks'].append({'component':'Replay, booking conflict and provider suppression','status':'PASS'})
                    health=app.get('/api/system-health').json()
                    assert next(x for x in health['checks'] if x['component']=='n8n API')['status']=='PASS'
                    report['checks'].append({'component':'System Health real n8n API read','status':'PASS'})
                    if screenshots:
                        render_previews(app,n8n,local,base,after['workflows']['MADAR Omnichannel Intake'])
                    # Exercise the bound Error Monitor with a real cross-tenant reference rejection.
                    error_flow={'name':'MADAR Acceptance Failure Fixture','nodes':[{'id':'start','name':'Start failure fixture','type':'n8n-nodes-base.manualTrigger','typeVersion':1,'position':[0,0],'parameters':{}},{'id':'input','name':'Prepare rejected customer reference','type':'n8n-nodes-base.code','typeVersion':2,'position':[300,0],'parameters':{'jsCode':"return [{json:{event_id:'negative-fixture',lead_id:'not-in-bound-tenant'}}];"}},{'id':'module','name':'Run actual qualification module','type':'n8n-nodes-base.executeWorkflow','typeVersion':1.2,'position':[600,0],'parameters':{'workflowId':{'__rl':True,'value':str(after['workflows']['MADAR Lead Intelligence']),'mode':'id'},'mode':'each','options':{'waitForSubWorkflow':True}}}],'connections':{'Start failure fixture':{'main':[[{'node':'Prepare rejected customer reference','type':'main','index':0}]]},'Prepare rejected customer reference':{'main':[[{'node':'Run actual qualification module','type':'main','index':0}]]}},'settings':{'errorWorkflow':str(after['workflows']['MADAR Error Monitor']),'saveDataSuccessExecution':'none','saveDataErrorExecution':'none'}}
                    created=n8n.post('/api/v1/workflows',headers={'X-N8N-API-KEY':key},json=error_flow);created.raise_for_status()
                    failure=subprocess.run(['docker','exec',name,'n8n','execute','--id='+created.json()['id']],env=docker_env,capture_output=True,text=True,timeout=60)
                    print('Expected error fixture exit:',failure.returncode,flush=True)
                    assert failure.returncode!=0
                    app.post('/api/auth/login',json={'workspace':'madar','email':'admin@madar.local','password':password}).raise_for_status()
                    # Error Monitor callback is async after parent failure; bounded wait.
                    for _ in range(50):
                        incidents=app.get('/api/state').json()['incidents']
                        if incidents:break
                        time.sleep(.1)
                    print('Redacted error incidents:',len(incidents),flush=True)
                    assert incidents and all(i['category']=='workflow_failure' for i in incidents)
                    report['checks'].append({'component':'Actual error routing and tenant reference rejection','status':'PASS'})
                    all_flows=n8n.get('/api/v1/workflows?limit=100',headers={'X-N8N-API-KEY':key}).json()['data']
                    assert not any(x['active'] for x in all_flows)
                    report['checks'].append({'component':'No workflow activation','status':'PASS'})
        finally:
            if server:
                server.terminate()
                try:server.wait(timeout=10)
                except subprocess.TimeoutExpired:server.kill();server.wait()
            # Only the randomly named container created above; no volume mounts or customer services.
            subprocess.run(['docker','rm','-f',name],env=docker_env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
    report['workflow_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'workflows').glob('*.json'))}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: isolated actual n8n acceptance; sanitized evidence written to',output)


def render_previews(app,n8n,local,base,workflow_id):
    def cookies(client):
        return [{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'httpOnly':True,'secure':False,'sameSite':'Lax'} for c in client.cookies.jar]
    payload={'app':local,'n8n':base,'appCookies':cookies(app),'n8nCookies':cookies(n8n),'workflowId':workflow_id,'root':str(ROOT)}
    code=r"""const fs=require('fs');const p=JSON.parse(fs.readFileSync(0,'utf8'));const {chromium}=require(p.root+'/frontend/node_modules/playwright');(async()=>{const browser=await chromium.launch({executablePath:process.env.MADAR_CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});try{const ctx=await browser.newContext({viewport:{width:1600,height:1050}});await ctx.addCookies(p.appCookies);const page=await ctx.newPage();await page.goto(p.app);await page.getByRole('button',{name:'System Health',exact:true}).click();await page.getByText('Verified',{exact:true}).waitFor();await page.getByRole('button',{name:'Evaluate agents',exact:true}).click();await page.getByText('Reply drafting agent',{exact:true}).waitFor();await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});await page.screenshot({path:p.root+'/docs/previews/enterprise-verified-demo.png',fullPage:true});await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('ar');await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});await page.screenshot({path:p.root+'/docs/previews/enterprise-verified-demo-arabic.png',fullPage:true});const nc=await browser.newContext({viewport:{width:1920,height:1080}});await nc.addCookies(p.n8nCookies);const np=await nc.newPage();await np.goto(p.n8n+'/workflow/'+p.workflowId);await np.locator('[data-test-id="canvas-node"]').first().waitFor({timeout:30000});const fit=np.locator('[data-test-id="zoom-to-fit"]');if(await fit.count())await fit.click();else await np.keyboard.press('f');await np.screenshot({path:p.root+'/docs/previews/actual-n8n-intake-canvas.png',fullPage:true});}finally{await browser.close();}})().catch(()=>{process.exit(1)});"""
    result=subprocess.run(['node','-e',code],input=json.dumps(payload),capture_output=True,text=True,timeout=90,cwd=ROOT)
    if result.returncode:raise RuntimeError('Optional Chromium preview failed; private cookies and browser output omitted')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--screenshots',action='store_true',help='Optional developer Chromium previews; never used by Windows startup')
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a new report path; existing evidence is preserved')
    try:acceptance(args.output,args.screenshots)
    except (httpx.HTTPError,RuntimeError,AssertionError,subprocess.SubprocessError,ValueError,KeyError) as error:
        print('FAIL: isolated acceptance did not complete ('+type(error).__name__+'). No credentials or execution payloads logged.',file=sys.stderr)
        if isinstance(error,RuntimeError):print(str(error),file=sys.stderr)
        raise SystemExit(1)
