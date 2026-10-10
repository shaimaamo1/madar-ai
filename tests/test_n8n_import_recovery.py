import json
from pathlib import Path

import httpx
import pytest

from scripts.n8n_deploy import deploy

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = {'N8N_BASE_URL': 'http://localhost:5678', 'N8N_API_KEY': 'test-key',
            'MADAR_BRIDGE_TOKEN': 'test-bridge', 'MADAR_INGEST_TOKEN': 'test-ingest'}


def test_lost_manifest_recovers_paginated_workflows_without_duplicate_imports(tmp_path):
    workflows, mutations, cursors = {}, [], []
    credential_count = 0
    def handler(request):
        nonlocal credential_count
        assert request.headers['X-N8N-API-KEY'] == 'test-key'
        path = request.url.path
        if request.method == 'GET' and path == '/api/v1/workflows':
            cursor = request.url.params.get('cursor')
            cursors.append(cursor)
            values = [{'id': w['id'], 'name': w['name'], 'active': w['active']} for w in workflows.values()]
            return httpx.Response(200, json={'data': values[2:] if cursor else values[:2],
                                           'nextCursor': 'page-two' if len(values) > 2 and not cursor else None})
        if request.method == 'GET':
            return httpx.Response(200, json=workflows[path.rsplit('/', 1)[1]])
        mutations.append((request.method, path))
        data = json.loads(request.content)
        if path == '/api/v1/credentials':
            credential_count += 1
            return httpx.Response(200, json={'id': str(credential_count)})
        if request.method == 'POST':
            identifier = str(len(workflows) + 1)
            workflows[identifier] = dict(data, id=identifier, active=False)
        else:
            identifier = path.rsplit('/', 1)[1]
            workflows[identifier].update(data)
        return httpx.Response(200, json=workflows[identifier])
    transport = httpx.MockTransport(handler)
    state = tmp_path / 'deployment.json'
    deploy(SETTINGS, transport=transport, state_path=state)
    state.unlink()
    mutations.clear()
    deploy(SETTINGS, transport=transport, state_path=state)
    assert len(workflows) == 4 and all(not w['active'] for w in workflows.values())
    assert not any(method == 'POST' and path == '/api/v1/workflows' for method, path in mutations)
    assert 'page-two' in cursors
    assert len(json.loads(state.read_text())['workflows']) == 4


@pytest.mark.parametrize('problem', ['duplicate', 'unrelated', 'active'])
def test_ambiguous_unrelated_or_active_imports_fail_before_any_mutation(tmp_path, problem):
    definition = json.loads((ROOT / 'workflows/madar-test-evaluation.json').read_text())
    current = dict(definition, id='existing', active=problem == 'active')
    if problem == 'unrelated':
        current['nodes'] = [{'id': 'foreign', 'type': 'n8n-nodes-base.manualTrigger'}]
    mutations = []
    def handler(request):
        if request.method != 'GET':
            mutations.append(request)
            return httpx.Response(500)
        if request.url.path == '/api/v1/workflows':
            rows = [{'name': definition['name'], 'id': 'existing'}]
            if problem == 'duplicate':
                rows.append({'name': definition['name'], 'id': 'second'})
            return httpx.Response(200, json={'data': rows})
        return httpx.Response(200, json=current)
    with pytest.raises(ValueError):
        deploy(SETTINGS, transport=httpx.MockTransport(handler), state_path=tmp_path / 'state.json')
    assert not mutations


def test_repeated_pagination_cursor_is_rejected_without_mutation(tmp_path):
    def handler(request):
        assert request.method == 'GET'
        return httpx.Response(200, json={'data': [], 'nextCursor': 'repeated'})
    with pytest.raises(ValueError, match='pagination'):
        deploy(SETTINGS, transport=httpx.MockTransport(handler), state_path=tmp_path / 'state.json')


def test_manifest_and_catalog_disagreement_cannot_create_duplicate_names(tmp_path):
    name = 'MADAR Test Evaluation'
    state = tmp_path / 'state.json'
    state.write_text(json.dumps({'base_url': SETTINGS['N8N_BASE_URL'], 'workflows': {name: 'old-renamed-id'}, 'credentials': {}}))
    def handler(request):
        assert request.method == 'GET'
        return httpx.Response(200, json={'data': [{'name': name, 'id': 'new-import-id'}]})
    with pytest.raises(ValueError, match='disagree'):
        deploy(SETTINGS, transport=httpx.MockTransport(handler), state_path=state)
