"""Local-only setup and checks. Invoke on the owner's computer, never via Cloud."""
import argparse
import getpass
import json
import os
import re
import secrets
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

from backend.urls import service_url

ROOT = Path(__file__).resolve().parent.parent


def load_settings(path):
    # Local .env wins over stale shell/cloud bindings. Never log this dictionary.
    return {**os.environ, **{k: v for k, v in dotenv_values(path, interpolate=False).items() if v is not None}}


def initialize(path, n8n_url=None, callback_url=None, container_url=None, replace_api_key=False):
    current = dotenv_values(path, interpolate=False) if path.exists() else {}
    if current.get('MADAR_ENV', 'development') != 'development':
        raise ValueError('Local setup refuses to change a production configuration')
    additions = {}
    for name, value in {
        'MADAR_ENV': 'development', 'MADAR_DEMO_MODE': 'true',
        'MADAR_PUBLIC_URL': 'http://localhost:8000',
        'N8N_ENABLED': 'true', 'N8N_BASE_URL': n8n_url or 'http://localhost:5678',
        'N8N_CONTAINER_URL': 'http://n8n:5678',
        'MADAR_N8N_APP_URL': callback_url or 'http://app:8000',
        'MADAR_INTEGRATION_WORKSPACE': 'madar',
        'MADAR_ADMIN_EMAIL': 'admin@madar.local',
        'MADAR_ALLOW_EXTERNAL_SEND': 'false', 'MADAR_ALLOW_MODEL_USAGE': 'false',
    }.items():
        if name not in current:
            additions[name] = value
    if n8n_url is not None:
        additions['N8N_BASE_URL'] = service_url(n8n_url, 'n8n')
    if callback_url is not None:
        additions['MADAR_N8N_APP_URL'] = service_url(callback_url, 'MADAR callback')
    if container_url is not None:
        additions['N8N_CONTAINER_URL'] = service_url(container_url, 'Container n8n')
    if current.get('N8N_ENABLED') != 'true':
        additions['N8N_ENABLED'] = 'true'
    additions = {name: value for name, value in additions.items() if current.get(name) != value}
    api_key = None if replace_api_key else current.get('N8N_API_KEY') or os.getenv('N8N_API_KEY')
    if not api_key:
        api_key = getpass.getpass('Local n8n API key (hidden; stored only in ignored .env): ').strip()
    if not api_key or any(ch in api_key for ch in '\r\n'):
        raise ValueError('Supply a nonempty single-line n8n API key')
    if replace_api_key or not current.get('N8N_API_KEY'):
        additions['N8N_API_KEY'] = api_key
    for name in ('MADAR_ADMIN_PASSWORD', 'MADAR_BRIDGE_TOKEN', 'MADAR_INGEST_TOKEN', 'N8N_ENCRYPTION_KEY'):
        if not current.get(name):
            additions[name] = secrets.token_urlsafe(32)
    existing = path.read_text() if path.exists() else '# Private local MADAR settings. Never commit this file.\n'
    if replace_api_key:
        existing = re.sub(r'^\s*(?:export\s+)?N8N_API_KEY\s*=.*\n?', '', existing, flags=re.MULTILINE)
    text = existing.rstrip() + '\n' + ''.join(f'{k}={json.dumps(v)}\n' for k, v in additions.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp-' + secrets.token_hex(4))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        if temporary.exists():
            temporary.unlink()
    print('Private .env saved (0600). Local tokens generated only when missing. No key values printed.')


def check(settings, transport=None, smoke=False):
    base = service_url(settings.get('N8N_BASE_URL', ''), 'n8n')
    key = settings.get('N8N_API_KEY')
    if not key:
        raise ValueError('N8N_API_KEY is missing. Run local init; do not paste keys into chat.')
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False, transport=transport) as client:
        response = client.get(base + '/api/v1/workflows', params={'limit': 1}, headers={'X-N8N-API-KEY': key})
        if response.is_error or response.is_redirect:
            raise ValueError(f'n8n read check failed (HTTP {response.status_code}); response body omitted')
        if not isinstance(response.json().get('data'), list):
            raise ValueError('n8n returned an unexpected workflow response')
        print('n8n API: workflow read access verified.')
        if not smoke:
            return
        if settings.get('MADAR_ENV', 'development') != 'development' or settings.get('MADAR_ALLOW_EXTERNAL_SEND', 'false') != 'false':
            raise ValueError('Smoke checks require development mode and external delivery disabled')
        app_url = service_url(settings.get('MADAR_TEST_APP_URL', settings.get('MADAR_PUBLIC_URL', 'http://localhost:8000')), 'MADAR')
        health = client.get(app_url + '/api/health')
        if health.status_code != 200 or health.json().get('service') != 'madar-ai':
            raise ValueError('MADAR health check failed')
        token = settings.get('MADAR_BRIDGE_TOKEN')
        if not token:
            raise ValueError('Local MADAR_BRIDGE_TOKEN is missing')
        evaluated = client.post(app_url + '/api/bridge/tick', headers={'Authorization': 'Bearer ' + token})
        if evaluated.status_code != 200 or 'queued' not in evaluated.json():
            raise ValueError(f'MADAR bridge check failed (HTTP {evaluated.status_code}); response body omitted')
        print('MADAR API and authenticated bridge verified. No dispatch endpoint called.')


def prepare(settings, output):
    callback = service_url(settings.get('MADAR_N8N_APP_URL', 'http://app:8000'), 'MADAR callback')
    output.mkdir(parents=True, exist_ok=True)
    for source in (ROOT / 'workflows').glob('*.json'):
        definition = json.loads(source.read_text())
        for node in definition['nodes']:
            if 'url' in node['parameters']:
                node['parameters']['url'] = node['parameters']['url'].replace('http://app:8000', callback)
            for credential in node.get('credentials', {}).values():
                credential.pop('id', None)
        (output / source.name).write_text(json.dumps(definition, indent=2) + '\n')
    print('Importable JSON prepared without secret values. All workflows remain inactive.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('command', choices=['init', 'check', 'test', 'prepare', 'deploy'])
    parser.add_argument('--n8n-url', help='Non-secret local base URL; never supply keys as arguments')
    parser.add_argument('--callback-url', help='Address reachable from n8n, e.g. http://app:8000')
    parser.add_argument('--container-url', help='Address reachable from the MADAR Docker container')
    parser.add_argument('--replace-api-key', action='store_true', help='Prompt securely for a replacement key; preserve other secrets')
    parser.add_argument('--output', type=Path, default=ROOT / 'var' / 'n8n-import')
    args = parser.parse_args()
    if args.command == 'init':
        initialize(args.env_file, args.n8n_url, args.callback_url, args.container_url, args.replace_api_key)
        return
    settings = load_settings(args.env_file)
    if args.n8n_url:
        settings['N8N_BASE_URL'] = args.n8n_url
    if args.callback_url:
        settings['MADAR_N8N_APP_URL'] = args.callback_url
    if args.command in ('check', 'test'):
        check(settings, smoke=args.command == 'test')
    elif args.command == 'prepare':
        prepare(settings, args.output)
    elif args.command == 'deploy':
        from scripts.n8n_deploy import deploy
        deploy(settings)


if __name__ == '__main__':
    try:
        main()
    except (httpx.HTTPError, ValueError, OSError):
        print('Local operation failed. Check URLs, API access, private .env, and Docker networking. No credentials logged.', file=sys.stderr)
        sys.exit(1)
