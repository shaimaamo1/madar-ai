import json
import stat
from pathlib import Path

import httpx
import pytest
from dotenv import dotenv_values

from backend.urls import service_url
from scripts.local_n8n import check, initialize, load_settings, prepare
from scripts.n8n_deploy import deploy


@pytest.mark.parametrize('url', ['http://localhost:5678', 'http://127.0.0.1:5678', 'http://[::1]:5678', 'http://n8n:5678', 'http://app:8000', 'http://host.docker.internal:8000', 'http://192.168.1.10:5678', 'https://automation.example.com/n8n'])
def test_supported_service_urls(url):
    assert service_url(url) == url


@pytest.mark.parametrize('url', ['', 'file:///tmp/secret', 'http://public.example.com', 'https://user:password@example.com', 'http://localhost:5678?token=secret', 'http://localhost:5678/#secret', 'http://localhost:bad', 'http://localhost:0', 'http://0.0.0.0:5678'])
def test_unsafe_service_urls(url):
    with pytest.raises(ValueError):
        service_url(url)


def test_local_secret_init_is_private_repeatable_and_never_prints_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv('N8N_API_KEY', raising=False)
    monkeypatch.setattr('scripts.local_n8n.getpass.getpass', lambda prompt: 'test-local-api-key')
    path = tmp_path / '.env'
    initialize(path)
    first = dotenv_values(path)
    initialize(path)
    second = dotenv_values(path)
    assert first == second
    assert len(first['MADAR_BRIDGE_TOKEN']) >= 40
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert 'test-local-api-key' not in capsys.readouterr().out
    assert 'MADAR_AI_API_KEY' not in first


def test_env_file_takes_precedence_over_stale_shell_configuration(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    path.write_text('N8N_BASE_URL=http://localhost:5678\nN8N_API_KEY=test-local\n')
    monkeypatch.setenv('N8N_BASE_URL', 'https://old.app.n8n.cloud')
    monkeypatch.setenv('N8N_API_KEY', 'stale-test-key')
    settings = load_settings(path)
    assert settings['N8N_API_KEY'] == 'test-local'
    assert settings['N8N_BASE_URL'] == 'http://localhost:5678'


def test_replacing_api_key_preserves_other_secrets_and_ignores_stale_shell(tmp_path, monkeypatch, capsys):
    path = tmp_path / '.env'
    path.write_text('N8N_API_KEY=old-test-key\nMADAR_BRIDGE_TOKEN=keep-bridge\nMADAR_INGEST_TOKEN=keep-ingest\nMADAR_ADMIN_PASSWORD=keep-test-password\nN8N_ENCRYPTION_KEY=keep-encryption\n')
    monkeypatch.setenv('N8N_API_KEY', 'stale-shell-test-key')
    monkeypatch.setattr('scripts.local_n8n.getpass.getpass', lambda prompt: 'replacement-test-key')
    initialize(path, replace_api_key=True)
    settings = dotenv_values(path)
    assert settings['N8N_API_KEY'] == 'replacement-test-key'
    assert settings['MADAR_BRIDGE_TOKEN'] == 'keep-bridge'
    assert settings['MADAR_INGEST_TOKEN'] == 'keep-ingest'
    assert settings['MADAR_ADMIN_PASSWORD'] == 'keep-test-password'
    assert settings['N8N_ENCRYPTION_KEY'] == 'keep-encryption'
    assert 'old-test-key' not in path.read_text()
    assert 'replacement-test-key' not in capsys.readouterr().out
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_invalid_replacement_does_not_change_private_configuration(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    content = 'N8N_API_KEY=existing-test-key\nMADAR_BRIDGE_TOKEN=keep-bridge\n'
    path.write_text(content)
    monkeypatch.setattr('scripts.local_n8n.getpass.getpass', lambda prompt: 'invalid\nkey')
    with pytest.raises(ValueError, match='single-line'):
        initialize(path, replace_api_key=True)
    assert path.read_text() == content


def test_local_checks_use_credentials_in_headers_and_never_dispatch(capsys):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path == '/api/v1/workflows':
            assert request.headers['X-N8N-API-KEY'] == 'test-key'
            return httpx.Response(200, json={'data': []})
        if request.url.path == '/api/health':
            return httpx.Response(200, json={'service': 'madar-ai', 'status': 'ok'})
        assert request.url.path == '/api/bridge/tick'
        assert request.headers['Authorization'] == 'Bearer test-bridge'
        return httpx.Response(200, json={'queued': 0})
    check({'N8N_BASE_URL': 'http://localhost:5678', 'N8N_API_KEY': 'test-key', 'MADAR_BRIDGE_TOKEN': 'test-bridge'}, transport=httpx.MockTransport(handler), smoke=True)
    assert len(calls) == 3 and all('test-key' not in str(r.url) for r in calls)
    assert 'test-key' not in capsys.readouterr().out


def test_redirect_never_forwards_credentials_to_another_host():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={'Location': 'http://other-host.invalid/steal'})
    with pytest.raises(ValueError, match='HTTP 302'):
        check({'N8N_BASE_URL': 'http://localhost:5678', 'N8N_API_KEY': 'test-key'}, transport=httpx.MockTransport(handler))
    assert len(calls) == 1


def test_prepared_workflows_contain_no_secret_values(tmp_path):
    prepare({'MADAR_N8N_APP_URL': 'http://host.docker.internal:8000', 'MADAR_BRIDGE_TOKEN': 'must-not-leak'}, tmp_path)
    files = list(tmp_path.glob('*.json'))
    assert len(files) == 10
    for path in files:
        text = path.read_text()
        assert 'must-not-leak' not in text
        workflow = json.loads(text)
        assert workflow['active'] is False
        for node in workflow['nodes']:
            if 'url' in node['parameters']:
                assert node['parameters']['url'].startswith('http://host.docker.internal:8000')


def test_deployment_is_inactive_idempotent_and_instance_scoped(tmp_path):
    workflows, credentials, calls = {}, {}, []
    def handler(request):
        calls.append((request.method, request.url.path))
        assert request.headers['X-N8N-API-KEY'] == 'test-key'
        path = request.url.path
        if path == '/api/v1/credentials':
            data = json.loads(request.content)
            credentials[data['name']] = data
            return httpx.Response(200, json={'id': str(len(credentials))})
        if path == '/api/v1/workflows' and request.method == 'GET':
            return httpx.Response(200, json={'data': []})
        if path == '/api/v1/workflows':
            data = json.loads(request.content)
            assert 'active' not in data
            identifier = str(len(workflows) + 1)
            workflows[identifier] = dict(data, id=identifier, active=False)
            return httpx.Response(200, json=workflows[identifier])
        identifier = path.rsplit('/', 1)[1]
        if request.method == 'GET':
            return httpx.Response(200, json=workflows[identifier])
        workflows[identifier].update(json.loads(request.content))
        return httpx.Response(200, json=workflows[identifier])
    settings = {'N8N_BASE_URL': 'http://localhost:5678', 'N8N_API_KEY': 'test-key', 'MADAR_BRIDGE_TOKEN': 'test-bridge', 'MADAR_INGEST_TOKEN': 'test-ingest'}
    transport = httpx.MockTransport(handler)
    state = tmp_path / 'deployment.json'
    deploy(settings, transport=transport, state_path=state)
    deploy(settings, transport=transport, state_path=state)
    assert len(workflows) == 10 and len(credentials) == 2
    assert all(not w['active'] for w in workflows.values())
    assert not any('activate' in path for _, path in calls)
    assert 'test-bridge' not in state.read_text()
    assert stat.S_IMODE(state.stat().st_mode) == 0o600
    workflows['1']['active'] = True
    with pytest.raises(ValueError, match='active workflow'):
        deploy(settings, transport=transport, state_path=state)
    with pytest.raises(ValueError, match='different n8n'):
        deploy({**settings, 'N8N_BASE_URL': 'http://127.0.0.1:5678'}, transport=transport, state_path=state)
