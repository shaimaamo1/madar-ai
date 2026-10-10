"""Generate importable self-hosted n8n workflow definitions without secrets."""
import json
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / 'workflows'
BASE = 'http://app:8000'


def http_node(name, endpoint, position):
    return {'id': name.lower().replace(' ', '-'), 'name': name, 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': position,
            'retryOnFail': True, 'maxTries': 3, 'waitBetweenTries': 2000,
            'parameters': {'method': 'POST', 'url': BASE + endpoint, 'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth', 'options': {'timeout': 30000}},
            'credentials': {'httpHeaderAuth': {'name': 'MADAR bridge'}}}


def write(name, nodes, connections):
    workflow = {'name': name, 'nodes': nodes, 'connections': connections, 'settings': {'executionOrder': 'v1', 'saveDataSuccessExecution': 'none', 'saveDataErrorExecution': 'all'}, 'active': False, 'tags': []}
    DEST.mkdir(exist_ok=True)
    (DEST / (name.lower().replace(' ', '-') + '.json')).write_text(json.dumps(workflow, indent=2) + '\n')


def main():
    trigger = {'id': 'schedule', 'name': 'Every five minutes', 'type': 'n8n-nodes-base.scheduleTrigger', 'typeVersion': 1.2, 'position': [200, 200], 'parameters': {'rule': {'interval': [{'field': 'minutes', 'minutesInterval': 5}]}}}
    write('MADAR Follow-up Scheduler', [trigger, http_node('Evaluate due follow-ups', '/api/bridge/tick', [440, 200]), http_node('Dispatch approved delivery', '/api/bridge/dispatch', [680, 200])], {'Every five minutes': {'main': [[{'node': 'Evaluate due follow-ups', 'type': 'main', 'index': 0}]]}, 'Evaluate due follow-ups': {'main': [[{'node': 'Dispatch approved delivery', 'type': 'main', 'index': 0}]]}})
    manual = {'id': 'manual', 'name': 'Safe manual test', 'type': 'n8n-nodes-base.manualTrigger', 'typeVersion': 1, 'position': [200, 200], 'parameters': {}}
    write('MADAR Test Evaluation', [manual, http_node('Evaluate due follow-ups', '/api/bridge/tick', [440, 200])], {'Safe manual test': {'main': [[{'node': 'Evaluate due follow-ups', 'type': 'main', 'index': 0}]]}})
    sub = {'id': 'sub', 'name': 'Called by workflow', 'type': 'n8n-nodes-base.executeWorkflowTrigger', 'typeVersion': 1.1, 'position': [200, 200], 'parameters': {'inputSource': 'passthrough'}}
    intake = http_node('Normalize inquiry', '/api/integrations/ingest', [440, 200])
    intake['parameters'].update({'sendBody': True, 'specifyBody': 'json', 'jsonBody': '={{ JSON.stringify($json) }}'})
    intake['credentials'] = {'httpHeaderAuth': {'name': 'MADAR ingestion'}}
    write('MADAR Ingestion Subworkflow', [sub, intake], {'Called by workflow': {'main': [[{'node': 'Normalize inquiry', 'type': 'main', 'index': 0}]]}})
    error = {'id': 'error', 'name': 'Workflow failure', 'type': 'n8n-nodes-base.errorTrigger', 'typeVersion': 1, 'position': [200, 200], 'parameters': {}}
    transform = {'id': 'summary', 'name': 'Redacted incident summary', 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': [440, 200], 'parameters': {'jsCode': "return $input.all().map(item => ({json: {workflowId: item.json.workflow?.id, executionId: item.json.execution?.id, timestamp: new Date().toISOString(), incident: 'Workflow failed; inspect restricted n8n execution logs'}}));"}}
    write('MADAR Error Monitor', [error, transform], {'Workflow failure': {'main': [[{'node': 'Redacted incident summary', 'type': 'main', 'index': 0}]]}})


if __name__ == '__main__':
    main()
