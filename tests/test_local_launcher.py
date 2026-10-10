"""Exercise the local launcher using fake Docker commands; no network access."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize('scenario,system,n8n_url,callback,replace_key', [
    ('docker', 'Linux', 'http://n8n:5678', 'http://app:8000', True),
    ('native', 'Linux', 'http://localhost:5678', 'http://localhost:8000', True),
    ('native', 'Linux', 'http://localhost:5678', 'http://localhost:8000', False),
    ('native', 'Darwin', 'http://host.docker.internal:5678', 'http://localhost:8000', True),
    ('alias_missing', 'Linux', 'http://172.20.0.7:5678', 'http://app:8000', True),
])
def test_launcher_routes_both_directions_and_keeps_secrets_out_of_commands(tmp_path, scenario, system, n8n_url, callback, replace_key):
    binary = tmp_path / 'bin'
    binary.mkdir()
    log = tmp_path / 'commands.jsonl'
    docker = binary / 'docker'
    docker.write_text('''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ['MADAR_FAKE_DOCKER_LOG'], 'a') as stream:
    stream.write(json.dumps(args)+'\\n')
scenario = os.environ['MADAR_FAKE_SCENARIO']
if args[0] == 'ps' and scenario != 'native':
    print('n8nio/n8n:test|owner-n8n')
if args[0] == 'inspect' and scenario == 'alias_missing':
    print('172.20.0.7' if '.IPAddress' in args[2] else '["owner-n8n"]')
''')
    docker.chmod(0o700)
    uname = binary / 'uname'
    uname.write_text('#!/bin/sh\nprintf "%s\\n" "$MADAR_FAKE_SYSTEM"\n')
    uname.chmod(0o700)
    env = dict(os.environ, PATH=str(binary)+os.pathsep+os.environ['PATH'],
               MADAR_FAKE_DOCKER_LOG=str(log), MADAR_FAKE_SCENARIO=scenario,
               MADAR_FAKE_SYSTEM=system)
    command = ['bash', 'scripts/local-dev.sh'] + (['--replace-api-key'] if replace_key else [])
    result = subprocess.run(command,
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    init = next(c for c in commands if 'init' in c)
    assert ('--replace-api-key' in init) == replace_key
    assert init[init.index('--callback-url')+1] == callback
    deploy = next(c for c in commands if 'deploy' in c)
    assert deploy[deploy.index('--n8n-url')+1] == n8n_url
    assert any('prepare' in c for c in commands)
    assert any('test' in c for c in commands)
    assert not any('activate' in c or 'down' in c for c in commands)
    uses_host = scenario == 'native' and system == 'Linux'
    assert ('docker-compose.host.yml' in deploy) == uses_host
    smoke = next(c for c in commands if 'test' in c)
    assert 'MADAR_TEST_APP_URL='+('http://localhost:8000' if uses_host else 'http://app:8000') in smoke
    assert not any('disconnect' in c for c in commands)
    assert 'N8N_API_KEY=' not in log.read_text()


def test_launcher_rejects_unexpected_arguments_before_docker():
    result = subprocess.run(['bash', 'scripts/local-dev.sh', '--unknown-option'],
                            cwd=ROOT, capture_output=True, text=True, timeout=5)
    assert result.returncode == 2
    assert 'Usage:' in result.stderr


@pytest.mark.parametrize('native_linux', [False, True])
def test_compose_private_credentials_and_loopback_networking(tmp_path, native_linux):
    if not shutil.which('docker'):
        pytest.skip('Docker CLI unavailable; Compose configuration cannot be checked')
    for name in ('docker-compose.yml', 'docker-compose.host.yml'):
        shutil.copyfile(ROOT / name, tmp_path / name)
    private = tmp_path / '.env'
    private.write_text('N8N_API_KEY=private-test-key\nMADAR_BRIDGE_TOKEN=private-test-bridge\nMADAR_ADMIN_PASSWORD=private-test-password\n')
    private.chmod(0o600)
    command = ['docker', 'compose', '-f', 'docker-compose.yml']
    if native_linux:
        command += ['-f', 'docker-compose.host.yml']
    command += ['config', '--format', 'json']
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=10,
                            env={'PATH': os.environ['PATH'], 'DOCKER_CONFIG': str(tmp_path / 'docker-config'),
                                 'N8N_API_KEY': 'stale-shell-test-key', 'MADAR_BRIDGE_TOKEN': 'stale-shell-test-bridge',
                                 'MADAR_ADMIN_PASSWORD': 'stale-shell-test-password'})
    assert result.returncode == 0, 'Compose configuration failed; expanded configuration omitted'
    app = json.loads(result.stdout)['services']['app']
    assert app['environment']['N8N_API_KEY'] == 'private-test-key'
    assert app['environment']['MADAR_BRIDGE_TOKEN'] == 'private-test-bridge'
    assert app['environment']['MADAR_ADMIN_PASSWORD'] == 'private-test-password'
    assert app['environment']['MADAR_ALLOW_EXTERNAL_SEND'] == 'false'
    assert app['environment']['MADAR_ALLOW_MODEL_USAGE'] == 'false'
    if native_linux:
        assert app['network_mode'] == 'host'
        assert not app.get('ports')
        assert app['command'][app['command'].index('--host')+1] == '127.0.0.1'
        assert app['environment']['N8N_BASE_URL'] == 'http://localhost:5678'
    else:
        assert app['ports'][0]['host_ip'] == '127.0.0.1'
