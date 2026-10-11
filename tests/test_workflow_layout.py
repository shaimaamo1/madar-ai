"""Guard the existing 327-node business contracts during canvas-only updates."""
import copy
import hashlib
import json
from pathlib import Path

import httpx

from scripts.n8n_deploy import deploy, workflow_templates
from scripts.workflow_layout import arrange
from scripts.workflow_quality import inspect_graph

ROOT = Path(__file__).resolve().parent.parent


def test_layout_preserves_all_existing_executable_nodes_and_business_contracts():
    baseline = json.loads((ROOT / 'tests/fixtures/workflow_semantics.json').read_text())
    flows = workflow_templates()
    assert len(flows) == len(baseline) == 14
    assert sum(len(f['nodes']) for f in flows) == 327
    for flow in flows:
        assert not any(n['type'].endswith('.stickyNote') for n in flow['nodes'])
        semantic = {**flow, 'nodes': [{k: v for k, v in n.items() if k != 'position'} for n in flow['nodes']]}
        assert hashlib.sha256(json.dumps(semantic, sort_keys=True).encode()).hexdigest() == baseline[flow['name']]['sha256']
        assert len(flow['nodes']) == baseline[flow['name']]['count']
        assert arrange(copy.deepcopy(flow['nodes']), flow['connections']) == flow['nodes']
        positions = {n['name']: n['position'] for n in flow['nodes']}
        for source, outputs in flow['connections'].items():
            for edges in outputs['main']:
                for edge in edges:
                    assert positions[edge['node']][0] > positions[source][0]
        for a in flow['nodes']:
            for b in flow['nodes']:
                if a['id'] != b['id'] and a['position'][0] == b['position'][0]:
                    assert abs(a['position'][1] - b['position'][1]) >= 260


def test_quality_rejects_reintroduced_decorations():
    flow = workflow_templates()[0]
    flow['nodes'].append({'id': 'decoration', 'name': 'Decoration', 'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1, 'position': [0, 0], 'parameters': {}})
    assert 'Decorative canvas nodes are forbidden' in inspect_graph(flow)['errors']


def test_decorated_enterprise_imports_update_in_place_even_without_manifest(tmp_path):
    versions = json.loads((ROOT / 'scripts/workflow_identity_versions.json').read_text())
    remote = {}
    for index, flow in enumerate(workflow_templates()):
        entries = versions[flow['name']]
        version = next((v for v in entries if v['version'].startswith('enterprise-before-clean')), entries[-1])
        remote[str(index)] = {'id': str(index), 'name': flow['name'], 'active': False,
                              'nodes': [{'id': nid, 'type': kind} for nid, kind in version['nodes']]}
    original_ids = {f['name']: f['id'] for f in remote.values()}
    updates = []
    def handler(request):
        path = request.url.path
        if path == '/api/v1/credentials':
            return httpx.Response(200, json={'id': 'fictional-header-credential'})
        if path == '/api/v1/workflows' and request.method == 'GET':
            return httpx.Response(200, json={'data': list(remote.values())})
        identifier = path.rsplit('/', 1)[1]
        if request.method == 'GET':
            return httpx.Response(200, json=remote[identifier])
        assert request.method == 'PUT', 'Existing workflows must never be duplicated'
        updates.append(identifier)
        remote[identifier] = dict(json.loads(request.content), id=identifier, active=False)
        return httpx.Response(200, json=remote[identifier])
    settings = {'N8N_BASE_URL': 'http://localhost:5678', 'N8N_API_KEY': 'fictional-test-key',
                'MADAR_BRIDGE_TOKEN': 'fictional-bridge', 'MADAR_INGEST_TOKEN': 'fictional-ingest'}
    for _ in range(2):
        deploy(settings, transport=httpx.MockTransport(handler), state_path=tmp_path/'manifest.json')
    assert len(updates) == 28
    assert {f['name']: f['id'] for f in remote.values()} == original_ids
    assert sum(len(f['nodes']) for f in remote.values()) == 327
    for flow in workflow_templates():
        deployed = remote[original_ids[flow['name']]]
        assert [(n['id'], n['position']) for n in deployed['nodes']] == [(n['id'], n['position']) for n in flow['nodes']]
        assert deployed['connections'] == flow['connections']
        assert not deployed['active']
