"""Reproducible n8n modules. All exports inactive; no credentials or fake nodes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'workflows'
BASE = 'http://app:8000'


def node(name, kind, pos, parameters=None, identifier=None):
    versions = {'httpRequest': 4.2, 'scheduleTrigger': 1.2, 'executeWorkflowTrigger': 1.1, 'executeWorkflow': 1.2, 'if': 2.2, 'code': 2, 'webhook': 2, 'respondToWebhook': 1.4, 'stickyNote': 1}
    return {'id': identifier or name.lower().replace(' ', '-'), 'name': name,
            'type': 'n8n-nodes-base.' + kind, 'typeVersion': versions.get(kind, 1), 'position': list(pos), 'parameters': parameters or {}}


def http_node(name, endpoint, position, body=None, credential='MADAR bridge'):
    parameters = {'method': 'POST', 'url': BASE + endpoint, 'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth', 'options': {'timeout': 30000}}
    if body is not None:
        parameters.update(sendBody=True, specifyBody='json', jsonBody=body)
    result = node(name, 'httpRequest', position, parameters)
    result.update(retryOnFail=True, maxTries=3, waitBetweenTries=2000, credentials={'httpHeaderAuth': {'name': credential}})
    return result


def code(name, text, pos, identifier=None):
    return node(name, 'code', pos, {'jsCode': text}, identifier)


def condition(name, expression, pos):
    return node(name, 'if', pos, {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict', 'version': 2},
                'conditions': [{'id': 'check', 'leftValue': expression, 'rightValue': '', 'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}], 'combinator': 'and'}, 'options': {}})


def group(title, pos, width, height, description):
    return node(title, 'stickyNote', pos, {'content': '## ' + title + '\n' + description, 'width': width, 'height': height, 'color': 5})


def connections(*paths):
    result = {}
    for source, target, *port in paths:
        output = port[0] if port else 0
        outputs = result.setdefault(source, {'main': []})['main']
        while len(outputs) <= output:
            outputs.append([])
        outputs[output].append({'node': target, 'type': 'main', 'index': 0})
    return result


def write(name, nodes, links):
    definition = {'name': name, 'nodes': nodes, 'connections': links, 'settings': {'executionOrder': 'v1', 'saveDataSuccessExecution': 'none', 'saveDataErrorExecution': 'none'}, 'active': False, 'tags': []}
    DEST.mkdir(exist_ok=True)
    (DEST / (name.lower().replace(' ', '-') + '.json')).write_text(json.dumps(definition, indent=2, ensure_ascii=False) + '\n')


def trigger(name='Called by workflow'):
    return node(name, 'executeWorkflowTrigger', (160, 220), {'inputSource': 'passthrough'}, 'sub')


def schedule(name, minutes=None):
    return node(name, 'scheduleTrigger', (160, 220), {'rule': {'interval': [{'field': 'minutes', 'minutesInterval': minutes}] if minutes else [{'field': 'days', 'triggerAtHour': 18}]}}, 'schedule')


def main():
    manual = node('Safe manual test', 'manualTrigger', (160, 220), identifier='manual')
    write('MADAR Test Evaluation', [manual, http_node('Evaluate due follow-ups', '/api/bridge/tick', (410, 220)), http_node('Read operational safeguards', '/api/bridge/status', (670, 220)), group('LOCAL ACCEPTANCE', (110, 100), 800, 250, 'Queues eligible records only. No dispatch, no activation, no paid inference.')], connections(('Safe manual test', 'Evaluate due follow-ups'), ('Evaluate due follow-ups', 'Read operational safeguards')))

    write('MADAR Follow-up Scheduler', [schedule('Every five minutes', 5), http_node('Evaluate due follow-ups', '/api/bridge/tick', (420, 220)), http_node('Read delivery authorization', '/api/bridge/status', (680, 220)), condition('Owner authorized delivery', '={{ $json.external_send_enabled === true }}', (940, 220)), http_node('Dispatch approved delivery', '/api/bridge/dispatch', (1200, 150)), code('Return queued sandbox status', "return [{json:{delivery:'disabled',queued:$('Evaluate due follow-ups').first().json.queued}}];", (1200, 340)), group('CONSENT AND RE-ENGAGEMENT', (100, 75), 790, 280, 'Backend enforces consent, opt-out, human takeover, due dates, reactivation and per-task idempotency.'), group('APPROVAL BOUNDARY', (900, 75), 520, 410, 'Provider dispatch independently re-checks authorization, messaging windows and attempt limits.')], connections(('Every five minutes', 'Evaluate due follow-ups'), ('Evaluate due follow-ups', 'Read delivery authorization'), ('Read delivery authorization', 'Owner authorized delivery'), ('Owner authorized delivery', 'Dispatch approved delivery'), ('Owner authorized delivery', 'Return queued sandbox status', 1)))

    validate = "return $input.all().map(({json})=>{if(!json.event_id||!json.lead?.name||typeof json.text!=='string') throw new Error('Expected normalized event_id, lead and text'); return {json};});"
    write('MADAR Ingestion Subworkflow', [trigger(), code('Validate normalized inquiry', validate, (400, 220)), http_node('Normalize inquiry', '/api/integrations/ingest', (650, 220), '={{ JSON.stringify($json) }}', 'MADAR ingestion'), group('ATOMIC CRM TRANSACTION', (110, 100), 810, 250, 'Receipt deduplication, contact resolution, qualification, scoring, inventory matching, assignment, history and gated outbox commit together.')], connections(('Called by workflow', 'Validate normalized inquiry'), ('Validate normalized inquiry', 'Normalize inquiry')))

    clean_incident = "return $input.all().map(({json})=>{const clean=v=>String(v||'').replace(/[^a-zA-Z0-9_-]/g,'').slice(0,100); const w=clean(json.workflow?.id),e=clean(json.execution?.id); return {json:{event_id:('failure:'+w+':'+e).slice(0,200),workflow_id:w,execution_id:e,category:'workflow_failure'}};});"
    write('MADAR Error Monitor', [node('Workflow failure', 'errorTrigger', (160, 220), identifier='error'), code('Redacted incident summary', clean_incident, (430, 220), 'summary'), http_node('Record operator incident', '/api/bridge/incidents', (700, 220), '={{ JSON.stringify($json) }}'), group('RESTRICTED INCIDENT ESCALATION', (110, 100), 850, 250, 'Identifiers only. Opens an auditable dashboard incident. No customer payloads, tokens, email or Slack notifications.')], connections(('Workflow failure', 'Redacted incident summary'), ('Redacted incident summary', 'Record operator incident')))

    webhook = node('Authenticated normalized events', 'webhook', (160, 220), {'httpMethod': 'POST', 'path': 'madar-intake', 'authentication': 'headerAuth', 'responseMode': 'responseNode', 'options': {}}, 'intake-webhook')
    webhook['webhookId'] = 'madar-normalized-intake'
    webhook['credentials'] = {'httpHeaderAuth': {'name': 'MADAR ingestion'}}
    normalize = "return $input.all().map(({json})=>{const body=json.body; if(!body||typeof body.event_id!=='string'||!body.lead||typeof body.text!=='string') throw new Error('Invalid normalized envelope'); if(body.text.length>4000) throw new Error('Message too long'); const lead={...body.lead,consent:body.lead.consent===true}; return {json:{event_id:body.event_id,lead,text:body.text}};});"
    call = node('Resolve sales intelligence', 'executeWorkflow', (950, 300), {'workflowId': {'__rl': True, 'value': 'MADAR_WORKFLOW:MADAR Lead Intelligence', 'mode': 'id'}, 'mode': 'each', 'options': {'waitForSubWorkflow': True}})
    reply = node('Acknowledge accepted event', 'respondToWebhook', (1450, 220), {'respondWith': 'json', 'responseBody': '={{ JSON.stringify({accepted:true,duplicate:$("CRM intake transaction").first().json.duplicate === true}) }}', 'options': {}})
    write('MADAR Omnichannel Intake', [webhook, code('Normalize trusted envelope', normalize, (420, 220)), http_node('CRM intake transaction', '/api/integrations/ingest', (680, 220), '={{ JSON.stringify($json) }}', 'MADAR ingestion'), condition('New event accepted', '={{ $json.duplicate !== true }}', (930, 100)), call, reply, group('AUTHENTICATED INTAKE', (100, 0), 770, 440, 'Website / CRM / authorized inbox sources send normalized events. Meta signatures terminate at MADAR /webhooks/meta, never at this JSON webhook.'), group('REPLAY AND CONTEXT', (890, 0), 780, 460, 'Duplicate events skip intelligence work. Import helper resolves subworkflow IDs. HTTP retries reuse stable event IDs.')], connections(('Authenticated normalized events', 'Normalize trusted envelope'), ('Normalize trusted envelope', 'CRM intake transaction'), ('CRM intake transaction', 'New event accepted'), ('New event accepted', 'Resolve sales intelligence'), ('New event accepted', 'Acknowledge accepted event', 1), ('Resolve sales intelligence', 'Acknowledge accepted event')))

    write('MADAR Lead Intelligence', [trigger(), code('Validate customer reference', "return $input.all().map(({json})=>{if(typeof json.lead_id!=='string'||!json.lead_id) throw new Error('lead_id required'); return {json:{lead_id:json.lead_id}};});", (400, 220)), http_node('Read intent score and inventory', '/api/bridge/intelligence', (670, 220), '={{ JSON.stringify($json) }}'), condition('Human adviser requested', '={{ $json.human_active === true }}', (950, 220)), http_node('Ensure adviser escalation task', '/api/bridge/handoff', (1230, 100), '={{ JSON.stringify({lead_id:$json.lead_id,active:true,reason:"Customer requested an adviser"}) }}'), code('Return actionable recommendations', "return $input.all().map(({json})=>({json:{lead_id:json.lead_id,intent:json.intent,score:json.score,next_action:json.next_action,missing_fields:json.missing_fields,assigned_agent_id:json.assigned_agent_id,recommendations:json.recommendations,followup_eligible:json.followup_eligible,template_required:json.template_required}}));", (1230, 340)), group('AUTHORITATIVE INTELLIGENCE', (110, 75), 810, 280, 'Arabic / English qualification and workload assignment happen atomically at ingestion. This module reads persisted CRM evidence and real available inventory.'), group('HUMAN OWNERSHIP', (920, 35), 580, 440, 'Persistent handoff pauses automated sales replies. Escalation tasks are deduplicated. Recommendations never fabricate listing facts.')], connections(('Called by workflow', 'Validate customer reference'), ('Validate customer reference', 'Read intent score and inventory'), ('Read intent score and inventory', 'Human adviser requested'), ('Human adviser requested', 'Ensure adviser escalation task'), ('Human adviser requested', 'Return actionable recommendations', 1)))

    validate_booking = "return $input.all().map(({json})=>{if(!json.event_id||!json.appointment?.lead_id||!json.appointment?.start_at) throw new Error('Expected booking event_id and explicit appointment'); return {json:{event_id:json.event_id,appointment:json.appointment}};});"
    write('MADAR Viewing Reservations', [trigger(), code('Validate explicit viewing request', validate_booking, (410, 220)), http_node('Reserve conflict-safe appointment', '/api/bridge/appointments', (680, 220), '={{ JSON.stringify($json) }}'), code('Return confirmed CRM booking', "return $input.all().map(({json})=>({json:{appointment_id:json.appointment.id,start_at:json.appointment.start_at,status:json.appointment.status,duplicate:json.duplicate}}));", (980, 220)), group('IDEMPOTENT RESERVATION', (110, 90), 1120, 270, 'Requires an explicit customer, listing, adviser and timezone-aware future time. SQLite transaction prevents all resource overlaps; changed replay payloads conflict.')], connections(('Called by workflow', 'Validate explicit viewing request'), ('Validate explicit viewing request', 'Reserve conflict-safe appointment'), ('Reserve conflict-safe appointment', 'Return confirmed CRM booking')))

    write('MADAR WhatsApp Delivery', [node('Operator delivery evaluation', 'manualTrigger', (160, 220), identifier='manual'), http_node('Read owner delivery authorization', '/api/bridge/status', (430, 220)), condition('Real delivery explicitly enabled', '={{ $json.external_send_enabled === true }}', (710, 220)), http_node('Dispatch eligible WhatsApp outbox', '/api/bridge/whatsapp/dispatch', (1010, 110)), code('Return sandbox boundary', "return [{json:{delivery:'disabled',provider_called:false,note:'Official Meta credentials and owner authorization required'}}];", (1010, 330)), group('OFFICIAL META ADAPTER', (110, 70), 770, 300, 'Credentials stay in MADAR server settings. No Graph tokens in n8n exports. This workflow is inactive and starts only on operator evaluation.'), group('PER-MESSAGE POLICY', (910, 30), 360, 460, 'Backend enforces opt-out, proactive consent, 24-hour service window, template shape and sandbox contact blocking. Uncertain requests are never auto-retried.')], connections(('Operator delivery evaluation', 'Read owner delivery authorization'), ('Read owner delivery authorization', 'Real delivery explicitly enabled'), ('Real delivery explicitly enabled', 'Dispatch eligible WhatsApp outbox'), ('Real delivery explicitly enabled', 'Return sandbox boundary', 1)))

    write('MADAR Sales Reporting', [schedule('Daily company reporting'), http_node('Compute tenant sales report', '/api/bridge/report', (430, 220)), code('Build executive report artifact', "return $input.all().map(({json})=>({json:{generated_at:json.generated_at,summary:json.summary,metrics:json.metrics,method:json.method,published:false}}));", (720, 220)), group('REAL CRM MEASUREMENT', (110, 90), 850, 270, 'Recorded sales, earned commissions, sources, response time and team conversion. Returns a report artifact; no email, public publishing or predicted revenue claims.')], connections(('Daily company reporting', 'Compute tenant sales report'), ('Compute tenant sales report', 'Build executive report artifact')))

    write('MADAR Delivery Reconciliation', [schedule('Review provider outcomes', 15), http_node('Escalate uncertain and failed delivery', '/api/bridge/reconcile', (460, 220)), condition('Incidents need operator review', '={{ $json.open_incidents > 0 }}', (780, 220)), code('Return reconciliation queue', "return [{json:{open_incidents:$json.open_incidents,new_incidents:$json.incidents_created,next_action:'Review dashboard incidents; reconcile provider outcome before retry'}}];", (1070, 110)), code('Return clean delivery review', "return [{json:{open_incidents:0,next_action:'No reconciliation required'}}];", (1070, 330)), group('RELIABILITY AND AUDIT', (110, 75), 900, 300, 'Retries: transient provider rejections only, exponential backoff, five attempts. Uncertain network outcomes create one operator incident per message; no blind replay.'), group('OPERATOR ESCALATION', (1010, 35), 360, 430, 'Dashboard-only incident queue. Customer text and provider errors are not copied to workflow logs or external notification accounts.')], connections(('Review provider outcomes', 'Escalate uncertain and failed delivery'), ('Escalate uncertain and failed delivery', 'Incidents need operator review'), ('Incidents need operator review', 'Return reconciliation queue'), ('Incidents need operator review', 'Return clean delivery review', 1)))


if __name__ == '__main__':
    main()
