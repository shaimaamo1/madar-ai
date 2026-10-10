import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import dotenv_values

from scripts.local_n8n import initialize

ROOT = Path(__file__).resolve().parent.parent


def test_windows_stdin_initialization_and_selected_port(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('N8N_API_KEY', 'stale-shell-test-key')
    path = tmp_path / '.env'
    path.write_text('N8N_API_KEY=old-test-key\nMADAR_ALLOW_EXTERNAL_SEND=true\nMADAR_ALLOW_MODEL_USAGE=true\nMADAR_BRIDGE_TOKEN=preserve-test-bridge\n')
    initialize(path, api_key_input='stdin-test-key', public_url='http://localhost:8001',
               callback_url='http://localhost:8001', container_url='http://host.docker.internal:5678', disable_external=True)
    settings = dotenv_values(path)
    assert settings['N8N_API_KEY'] == 'stdin-test-key'
    assert settings['MADAR_PORT'] == '8001'
    assert settings['MADAR_PUBLIC_URL'] == 'http://localhost:8001'
    assert settings['MADAR_BRIDGE_TOKEN'] == 'preserve-test-bridge'
    assert settings['MADAR_ALLOW_EXTERNAL_SEND'] == settings['MADAR_ALLOW_MODEL_USAGE'] == 'false'
    assert 'old-test-key' not in path.read_text()
    assert 'stdin-test-key' not in capsys.readouterr().out


def test_empty_private_stdin_never_falls_back_to_interactive_prompt(tmp_path, monkeypatch):
    def unsafe_prompt(prompt):
        raise AssertionError('Empty stdin must fail without prompting or echoing input')
    monkeypatch.setattr('scripts.local_n8n.getpass.getpass', unsafe_prompt)
    with pytest.raises(ValueError, match='single-line'):
        initialize(tmp_path / '.env', api_key_input='')
    assert not (tmp_path / '.env').exists()


def test_windows_compose_cannot_create_n8n_and_uses_private_settings(tmp_path):
    if not shutil.which('docker'):
        pytest.skip('Docker CLI unavailable for Compose validation')
    shutil.copyfile(ROOT / 'docker-compose.windows.yml', tmp_path / 'docker-compose.windows.yml')
    private = tmp_path / '.madar-local'
    private.mkdir()
    env = private / '.env'
    env.write_text('N8N_API_KEY=private-test-key\nMADAR_PORT=8001\nMADAR_ALLOW_EXTERNAL_SEND=true\nMADAR_ALLOW_MODEL_USAGE=true\n')
    command = ['docker', 'compose', '--env-file', str(env), '-f', 'docker-compose.windows.yml', 'config', '--format', 'json']
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True,
                            env={'PATH': os.environ['PATH'], 'DOCKER_CONFIG': str(tmp_path / 'docker'), 'N8N_API_KEY': 'stale-test-key'})
    assert result.returncode == 0, 'Compose failed; expanded output omitted'
    import json
    services = json.loads(result.stdout)['services']
    assert list(services) == ['app']
    app = services['app']
    assert app['environment']['N8N_API_KEY'] == 'private-test-key'
    assert app['environment']['MADAR_ALLOW_EXTERNAL_SEND'] == app['environment']['MADAR_ALLOW_MODEL_USAGE'] == 'false'
    assert app['ports'][0]['published'] == '8001' and app['ports'][0]['host_ip'] == '127.0.0.1'


def test_powershell_orchestration_without_windows_or_network(tmp_path):
    pwsh = os.getenv('MADAR_PWSH_PATH') or shutil.which('pwsh')
    if not pwsh:
        pytest.skip('PowerShell unavailable; Windows launcher orchestration not executed')
    result = subprocess.run([pwsh, '-NoProfile', '-File', str(ROOT / 'tests/windows_launcher.tests.ps1'),
                             '-RepoRoot', str(ROOT), '-OutputRoot', str(tmp_path)], capture_output=True, text=True,
                            env=dict(os.environ, XDG_CACHE_HOME=str(tmp_path / 'cache'), XDG_CONFIG_HOME=str(tmp_path / 'config'),
                                     XDG_DATA_HOME=str(tmp_path / 'data')), timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '13 scenarios PASS' in result.stdout
    assert 'test-private-stdin-key' not in result.stdout + result.stderr


def test_powershell_native_process_receives_key_only_via_stdin(tmp_path):
    pwsh = os.getenv('MADAR_PWSH_PATH') or shutil.which('pwsh')
    if not pwsh or os.name == 'nt':
        pytest.skip('Requires PowerShell Core and a Unix executable fixture')
    executable = tmp_path / 'fake docker'
    executable.write_text('''#!/usr/bin/env python3
import hashlib,json,sys
value=sys.stdin.read().strip()
print(json.dumps({'argv':sys.argv[1:],'stdin_hash':hashlib.sha256(value.encode()).hexdigest()}))
''')
    executable.chmod(0o700)
    script = tmp_path / 'native-stdin.ps1'
    script.write_text('''$ErrorActionPreference='Stop'
. (Join-Path $env:MADAR_TEST_ROOT 'scripts/windows/Madar.Local.ps1')
$script:MadarDockerExe=$env:MADAR_TEST_EXECUTABLE
$result=Invoke-MadarDocker -DockerArgs @('compose','run','C:\\Projects with spaces:/workspace','--api-key-stdin') -InputText 'private-native-stdin-test'
if ($result.ExitCode -ne 0) { throw 'Native process failed' }
$result.Output
''')
    result = subprocess.run([pwsh, '-NoProfile', '-File', str(script)],capture_output=True,text=True,timeout=15,
                            env=dict(os.environ,MADAR_TEST_ROOT=str(ROOT),MADAR_TEST_EXECUTABLE=str(executable),
                                     XDG_CACHE_HOME=str(tmp_path/'cache'),XDG_CONFIG_HOME=str(tmp_path/'config'),XDG_DATA_HOME=str(tmp_path/'data')))
    assert result.returncode == 0, 'PowerShell native stdin invocation failed; output omitted'
    import hashlib,json
    received = json.loads(result.stdout)
    assert received['argv'] == ['compose','run','C:\\Projects with spaces:/workspace','--api-key-stdin']
    assert received['stdin_hash'] == hashlib.sha256(b'private-native-stdin-test').hexdigest()
    assert 'private-native-stdin-test' not in result.stdout + result.stderr


def test_private_acl_algorithm_and_safe_diagnostics(tmp_path):
    pwsh = os.getenv('MADAR_PWSH_PATH') or shutil.which('pwsh')
    if not pwsh:
        pytest.skip('PowerShell unavailable; simulated ACL regression not executed')
    result = subprocess.run([pwsh, '-NoProfile', '-File', str(ROOT / 'tests/windows_private_acl.tests.ps1'),
                             '-RepoRoot', str(ROOT), '-OutputRoot', str(tmp_path / 'fixture')],
                            capture_output=True, text=True, timeout=30,
                            env=dict(os.environ, XDG_CACHE_HOME=str(tmp_path / 'cache'),
                                     XDG_CONFIG_HOME=str(tmp_path / 'config'), XDG_DATA_HOME=str(tmp_path / 'data')))
    assert result.returncode == 0, result.stdout + result.stderr
    assert '16 scenarios PASS' in result.stdout
    assert 'secret-env-value' not in result.stdout + result.stderr


def test_private_acl_native_windows(tmp_path):
    if os.name != 'nt':
        pytest.skip('Actual Windows ACLs and PowerShell 5.1 require Windows; not verified here')
    powershell = shutil.which('powershell.exe')
    if not powershell:
        pytest.skip('Windows PowerShell 5.1 unavailable')
    result = subprocess.run([powershell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                             str(ROOT / 'tests/windows_private_acl.native.tests.ps1'),
                             '-RepoRoot', str(ROOT), '-OutputRoot', str(tmp_path / 'fixture')],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, 'Native Windows ACL regression failed; inspect locally without sharing credentials'
    assert 'Native Windows ACL: PASS' in result.stdout
