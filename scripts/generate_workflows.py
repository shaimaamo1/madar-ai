"""Generate eight substantive business canvases and inactive reusable support modules."""
import json
from scripts.generate_support_workflows import DEST, node, code, http_node, condition, connections, write, trigger, main as support
from scripts.enterprise_stages import STAGES, NAMES


def call(name,target,pos):
    return node(name,'executeWorkflow',pos,{'workflowId':{'__rl':True,'value':'MADAR_WORKFLOW:'+target,'mode':'id'},'mode':'each','options':{'waitForSubWorkflow':True}})


def main():
    support()  # Retain tested delivery, reconciliation, incident and reusable intake contracts.
    for kind, stages in STAGES.items():
        nodes=[trigger()]
        paths=[]
        entry=code('Normalize trusted envelope' if kind=='intake' else 'Validate orchestration envelope',
            "return $input.all().map(({json})=>{let b=json.body||json;if(json.body){if(typeof b.event_id!=='string'||!b.lead||typeof b.text!=='string')throw new Error('Invalid normalized envelope');b={...b,lead:{...b.lead,consent:b.lead.consent===true}};}if(!b.event_id)throw new Error('Stable event_id required');const allowed=['event_id','lead_id','run_id','run_token','lead','text','appointment'];const out={kind:"+json.dumps(kind)+"};for(const k of allowed)if(b[k]!==undefined && (k!=='appointment'||out.kind==='appointment') && (!['lead','text'].includes(k)||out.kind==='intake'))out[k]=b[k];return {json:out};});",(420,220))
        nodes.append(entry)
        paths.append(('Called by workflow',entry['name']))
        if kind=='intake':
            hook=node('Authenticated normalized events','webhook',(140,430),{'httpMethod':'POST','path':'madar-intake','authentication':'headerAuth','responseMode':'responseNode','options':{}},'intake-webhook')
            hook['webhookId']='madar-normalized-intake';hook['credentials']={'httpHeaderAuth':{'name':'MADAR ingestion'}}
            nodes.append(hook);paths.append((hook['name'],entry['name']))
        elif kind in ('followup','reporting'):
            schedule=node('Every five minutes' if kind=='followup' else 'Daily company reporting','scheduleTrigger',(140,430),{'rule':{'interval':[{'field':'minutes','minutesInterval':5}] if kind=='followup' else [{'field':'days','triggerAtHour':18}]}},'schedule')
            bootstrap=code('Generate scheduled receipt identity',"return [{json:{event_id:'scheduled:'+String($execution.id)}}];",(140,650))
            nodes.extend([schedule,bootstrap]);paths.extend([(schedule['name'],bootstrap['name']),(bootstrap['name'],entry['name'])])
        context=http_node('Read tenant-scoped business context','/api/bridge/enterprise/context',(710,220),'={{ JSON.stringify($json) }}')
        context['onError']='continueErrorOutput'
        nodes.append(context);paths.append((entry['name'],context['name']));previous=context['name']
        # Business stages retain their validated parameters and error branches.
        for index,stage in enumerate(stages):
            name,key,expression,*gate=stage
            col=index%4;row=index//4
            x=1060+col*650;y=220+row*550
            src="return $input.all().map(({json:s})=>{const r=s.inquiry||s.request,l=s.lead,a=s.analysis;a["+json.dumps(key)+"]=("+expression+");return {json:s};});"
            process=code(name,src,(x,y));nodes.append(process);paths.append((previous,name));previous=name
            if gate:
                guard=condition(name+' accepted','={{ $json.analysis.'+key+' === true }}',(x+270,y))
                failure=code(name+' review required',"return $input.all().map(({json:s})=>({json:{...s.request,execution_id:String($execution.id),reason:'validation_failed'}}));",(x+270,y+190))
                nodes.extend([guard,failure]);paths.extend([(previous,guard['name']),(guard['name'],failure['name'],1)]);previous=guard['name']
                paths.append((failure['name'],'Record scoped failure incident'))
        commit=http_node('Commit authoritative '+kind,'/api/bridge/enterprise/commit',(3820,1870),'={{ JSON.stringify({...$json.request,analysis:$json.analysis,execution_id:String($execution.id)}) }}')
        commit['onError']='continueErrorOutput'
        nodes.append(commit);paths.append((previous,commit['name']))
        trap=code('Redact backend rejection',"const r=$("+json.dumps(entry['name'])+").first().json;return [{json:{...r,execution_id:String($execution.id),reason:'backend_failed'}}];",(3820,2170))
        failed=http_node('Record scoped failure incident','/api/bridge/enterprise/failure',(4130,2350),'={{ JSON.stringify($json) }}')
        stop=code('Stop rejected business execution',"throw new Error('MADAR business execution failed. Review the scoped dashboard incident; payload omitted.');",(4440,2350))
        nodes.extend([trap,failed,stop]);paths.extend([(context['name'],trap['name'],1),(commit['name'],trap['name'],1),(trap['name'],failed['name']),(failed['name'],stop['name'])])
        if kind != 'intake':
            receipt=code('Return minimal orchestration receipt',"return $input.all().map(({json:r})=>({json:{kind:r.kind,event_id:r.event_id,run_id:r.run_id,run_token:r.run_token,lead_id:r.lead_id,duplicate:r.duplicate,mode:r.mode,external_messages_sent:r.external_messages_sent}}));",(4100,1870))
            nodes.append(receipt);paths.append((commit['name'],receipt['name']))
        if kind=='intake':
            fresh=condition('New event requires intelligence','={{ $json.duplicate !== true }}',(4050,1700))
            nodes.append(fresh);paths.append((commit['name'],fresh['name']))
            intelligence=call('Resolve sales intelligence',NAMES['qualification'],(4100,1870));nodes.append(intelligence);paths.append((fresh['name'],intelligence['name']))
            # A webhook response must not execute when this workflow is called as a module.
            ishook=condition('HTTP request requires acknowledgement',"={{ $('Normalize trusted envelope').first().json.run_id === undefined }}",(4380,1870))
            response=node('Acknowledge accepted event','respondToWebhook',(4670,1780),{'respondWith':'json','responseBody':'={{ JSON.stringify({accepted:true,lead_id:$json.lead_id,duplicate:$json.duplicate===true}) }}','options':{}})
            returned=code('Return scoped module result','return $input.all().map(item=>({json:item.json}));',(4670,1990))
            # Normal non-demo executeWorkflow intake also lacks run_id: detect actual webhook execution instead.
            ishook['parameters']['conditions']['conditions'][0]['leftValue']="={{ $('Authenticated normalized events').isExecuted }}"
            nodes.extend([ishook,response,returned]);paths.extend([(intelligence['name'],ishook['name']),(ishook['name'],response['name']),(ishook['name'],returned['name'],1)])
            paths.append((fresh['name'],ishook['name'],1))
        write(NAMES[kind],nodes,connections(*paths))
    manual=node('Run queued fictional demo','manualTrigger',(120,260),identifier='manual')
    claim=http_node('Claim isolated demo capability','/api/bridge/demo/claim',(400,260))
    nodes=[manual,claim];paths=[(manual['name'],claim['name'])];previous=claim['name']
    for index,kind in enumerate(STAGES):
        step=call('Run '+kind+' module',NAMES[kind],(750+index*290,260));nodes.append(step);paths.append((previous,step['name']));previous=step['name']
    finish=http_node('Record actual execution reference','/api/bridge/demo/complete',(3180,260),'={{ JSON.stringify({run_id:$json.run_id,run_token:$json.run_token,execution_id:String($execution.id)}) }}')
    nodes.append(finish);paths.append((previous,finish['name']))
    write('MADAR Full Demo',nodes,connections(*paths))
    # n8n deletes execution metadata together with payloads under "none".
    # Keep success evidence ONLY for the server-controlled fictional demo;
    # its capability is revoked before completion. Customer workflows retain none.
    demo_path = DEST / 'madar-full-demo.json'
    demo = json.loads(demo_path.read_text())
    demo['settings']['saveDataSuccessExecution'] = 'all'
    demo_path.write_text(json.dumps(demo, indent=2, ensure_ascii=False) + '\n')


if __name__=='__main__':
    main()
