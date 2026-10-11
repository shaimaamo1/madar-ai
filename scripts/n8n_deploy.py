"""Idempotent API deployment of inactive workflows to operator-configured n8n."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import httpx

from backend.urls import service_url

ROOT = Path(__file__).resolve().parent.parent


def workflow_templates():
    definitions = [json.loads(path.read_text()) for path in sorted((ROOT / 'workflows').glob('*.json'))]
    by_name = {item['name']: item for item in definitions}
    ordered, visiting, done = [], set(), set()
    def visit(name):
        if name in done:
            return
        if name in visiting or name not in by_name:
            raise ValueError('Workflow dependency is cyclic or missing')
        visiting.add(name)
        for node in by_name[name]['nodes']:
            target = node.get('parameters', {}).get('workflowId', {})
            value = target.get('value', '') if isinstance(target, dict) else ''
            if value.startswith('MADAR_WORKFLOW:'):
                visit(value.removeprefix('MADAR_WORKFLOW:'))
        visiting.remove(name)
        done.add(name)
        ordered.append(by_name[name])
    visit('MADAR Error Monitor')
    for name in sorted(by_name):
        visit(name)
    return ordered


def deploy(settings, transport=None, state_path=None):
    base = service_url(settings.get('N8N_BASE_URL', ''), 'n8n')
    callback = service_url(settings.get('MADAR_N8N_APP_URL', 'http://app:8000'), 'MADAR callback')
    api_key = settings.get('N8N_API_KEY')
    bridge, ingest = settings.get('MADAR_BRIDGE_TOKEN'), settings.get('MADAR_INGEST_TOKEN')
    if not api_key or not bridge or not ingest:
        raise ValueError('n8n key and local bridge/ingestion tokens are required')
    local = state_path or ROOT / 'var' / 'n8n-deployments' / (hashlib.sha256(base.encode()).hexdigest()[:16] + '.json')
    local.parent.mkdir(parents=True, exist_ok=True)
    saved = json.loads(local.read_text()) if local.exists() else {'base_url': base, 'workflows': {}, 'credentials': {}}
    if saved.get('base_url') != base:
        raise ValueError('Deployment state belongs to a different n8n instance')
    def persist():
        temporary = local.with_suffix('.tmp')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(saved, stream, indent=2)
        os.replace(temporary, local)
    with httpx.Client(base_url=base + '/api/v1/', headers={'X-N8N-API-KEY': api_key}, timeout=30, trust_env=False, follow_redirects=False, transport=transport) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            if response.is_error or response.is_redirect:
                raise ValueError(f'n8n operation failed (HTTP {response.status_code}); response body omitted')
            return response.json()
        # Preflight every template before mutations. Recover workflows after a lost
        # manifest or a manual import, while refusing ambiguous names and takeovers.
        templates = workflow_templates()
        legacy = json.loads((ROOT / 'scripts' / 'legacy_workflow_identities.json').read_text())
        versions = json.loads((ROOT / 'scripts' / 'workflow_identity_versions.json').read_text())
        catalog, cursors, cursor = [], set(), None
        while True:
            page = request('GET', 'workflows', params={'limit': 100, **({'cursor': cursor} if cursor else {})})
            if not isinstance(page.get('data'), list):
                raise ValueError('n8n returned an unexpected workflow list')
            catalog.extend(page['data'])
            cursor = page.get('nextCursor')
            if not cursor:
                break
            if cursor in cursors:
                raise ValueError('n8n workflow pagination repeated a cursor')
            cursors.add(cursor)
        for definition in templates:
            matches = [w for w in catalog if w.get('name') == definition['name']]
            if len(matches) > 1:
                raise ValueError('Multiple same-name workflows exist; resolve ambiguity locally before import')
            previous = saved['workflows'].get(definition['name'])
            if previous and matches and str(matches[0]['id']) != str(previous):
                raise ValueError('Manifest ID and same-name workflow disagree; resolve the conflict locally')
            if previous:
                current = request('GET', 'workflows/' + str(previous))
            elif matches:
                current = request('GET', 'workflows/' + str(matches[0]['id']))
                expected = {(n['id'], n['type']) for n in definition['nodes']}
                actual = {(n.get('id'), n.get('type')) for n in current.get('nodes', [])}
                previous_version = {tuple(n) for n in legacy.get(definition['name'], [])}
                known_versions = [{tuple(n) for n in v['nodes']} for v in versions.get(definition['name'], [])]
                if actual != expected and actual != previous_version and actual not in known_versions:
                    raise ValueError('An unrelated same-name workflow exists; refusing to overwrite or duplicate it')
                saved['workflows'][definition['name']] = current['id']
            else:
                continue
            if current.get('active'):
                raise ValueError('Refusing to update an active workflow; deactivate the managed test workflow first')
        for name, value in [('MADAR bridge', bridge), ('MADAR ingestion', ingest)]:
            payload = {'name': name, 'type': 'httpHeaderAuth', 'data': {'name': 'Authorization', 'value': 'Bearer ' + value}}
            if name not in saved['credentials']:
                result = request('POST', 'credentials', json=payload)
                saved['credentials'][name] = result['id']
                persist()
        error_id = None
        for definition in templates:
            is_error = definition['name'] == 'MADAR Error Monitor'
            for node in definition['nodes']:
                if 'url' in node['parameters']:
                    node['parameters']['url'] = node['parameters']['url'].replace('http://app:8000', callback)
                for credential in node.get('credentials', {}).values():
                    credential['id'] = saved['credentials'][credential['name']]
                target = node['parameters'].get('workflowId', {})
                if isinstance(target, dict) and str(target.get('value', '')).startswith('MADAR_WORKFLOW:'):
                    name = target['value'].removeprefix('MADAR_WORKFLOW:')
                    target['value'] = str(saved['workflows'][name])
            if error_id and not is_error:
                definition['settings']['errorWorkflow'] = error_id
            body = {k: definition[k] for k in ('name', 'nodes', 'connections', 'settings')}
            previous = saved['workflows'].get(definition['name'])
            if previous:
                current = request('GET', 'workflows/' + str(previous))
                if current.get('active'):
                    raise ValueError('Refusing to update an active workflow; deactivate the managed test workflow first')
                result = request('PUT', 'workflows/' + str(previous), json=body)
            else:
                result = request('POST', 'workflows', json=body)
            saved['workflows'][definition['name']] = result['id']
            persist()
            if is_error:
                error_id = str(result['id'])
            print('Saved inactive workflow:', definition['name'])
    print('No workflows activated. No customer messages sent.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    args = parser.parse_args()
    from scripts.local_n8n import check, load_settings
    settings = load_settings(args.env_file)
    if args.check:
        check(settings)
    else:
        deploy(settings)


if __name__ == '__main__':
    try:
        main()
    except (httpx.HTTPError, ValueError, OSError):
        print('n8n operation failed. Check local configuration and API permissions; no credentials logged.', file=sys.stderr)
        sys.exit(1)
