"""Real fast-forward/failure fixtures; never contact GitHub, Docker or owner data."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def git(folder, *args, check=True):
    return subprocess.run(['git', '-C', str(folder), *args], check=check, capture_output=True, text=True)


@pytest.mark.parametrize('scenario', ['success', 'already-current', 'wrong-branch', 'dirty-tracked', 'untracked', 'diverged', 'fetch-failure', 'backup-failure'])
def test_safe_windows_update_with_real_local_git(tmp_path, scenario):
    pwsh = os.getenv('MADAR_PWSH_PATH') or shutil.which('pwsh')
    if not pwsh or not shutil.which('git'):
        pytest.skip('PowerShell Core/Git needed for local update fixture')
    source, remote, checkout = [tmp_path / name for name in ('source', 'remote.git', 'checkout')]
    source.mkdir()
    git(source, 'init', '-b', 'codex/self-hosted-n8n')
    git(source, 'config', 'user.name', 'Fictional update fixture')
    git(source, 'config', 'user.email', 'fixture@example.invalid')
    (source / '.gitignore').write_text('.madar-local/\n')
    (source / 'version.txt').write_text('old')
    launcher = source / 'scripts/windows/Madar.Local.ps1'
    launcher.parent.mkdir(parents=True)
    launcher.write_text("function Start-MadarLocal { param([string]$RepoRoot,[switch]$NoBrowser) $script:Started=$true; return $true }\n")
    git(source, 'add', '.')
    git(source, 'commit', '-m', 'Fictional prior version')
    subprocess.run(['git', 'clone', '--bare', str(source), str(remote)], check=True, capture_output=True)
    subprocess.run(['git', 'clone', str(remote), str(checkout)], check=True, capture_output=True)
    git(checkout, 'config', 'user.name', 'Fictional update fixture')
    git(checkout, 'config', 'user.email', 'fixture@example.invalid')
    git(checkout, 'remote', 'set-url', 'origin', 'https://github.com/shaimaamo1/madar-ai.git')
    # Keep the expected public origin identity, route every Git operation to a local
    # fixture via environment-scoped rewrite. No global Git configuration edits.
    replacement = tmp_path / 'missing.git' if scenario == 'fetch-failure' else remote
    env = dict(os.environ, GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0=f'url.{replacement}.insteadOf', GIT_CONFIG_VALUE_0='https://github.com/shaimaamo1/madar-ai.git',
               XDG_CACHE_HOME=str(tmp_path/'cache'), XDG_CONFIG_HOME=str(tmp_path/'config'), XDG_DATA_HOME=str(tmp_path/'data'))
    private = checkout / '.madar-local'
    private.mkdir()
    (private / '.env').write_text('N8N_API_KEY=private-test-secret\nMADAR_BRIDGE_TOKEN=unchanged-private-test\n')
    if scenario != 'already-current':
        (source / 'version.txt').write_text('new')
        git(source, 'commit', '-am', 'Fictional new version')
        git(source, 'push', str(remote), 'codex/self-hosted-n8n')
    if scenario == 'wrong-branch':
        git(checkout, 'switch', '-c', 'other-branch')
    if scenario == 'dirty-tracked':
        (checkout/'version.txt').write_text('user change must survive')
    if scenario == 'untracked':
        (checkout/'customer-note.txt').write_text('local file must survive')
    if scenario == 'diverged':
        (checkout/'local.txt').write_text('user local commit must survive')
        git(checkout, 'add', 'local.txt')
        git(checkout, 'commit', '-m', 'Local changes')
    result = subprocess.run([pwsh, '-NoProfile', '-File', str(ROOT/'tests/windows_update.tests.ps1'),
                             '-RepoRoot', str(ROOT), '-FixtureRoot', str(checkout), '-GitExe', shutil.which('git'), '-Scenario', scenario],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Update fixture PASS:' in result.stdout
    if scenario not in ('success', 'already-current'):
        step = 'Recovery backup' if scenario == 'backup-failure' else 'Fetch target branch' if scenario in ('fetch-failure','diverged') else 'Clean update checkout'
        assert re.search(re.escape(step) + r'\s+FAIL', result.stdout)
    assert 'private-test-secret' not in result.stdout + result.stderr
    assert 'unchanged-private-test' not in result.stdout + result.stderr
    assert not (checkout/'var').exists()
    if scenario == 'dirty-tracked':
        assert (checkout/'version.txt').read_text() == 'user change must survive'
    if scenario == 'untracked':
        assert (checkout/'customer-note.txt').read_text() == 'local file must survive'


def test_cmd_wrappers_keep_exit_status_and_use_existing_launchers():
    for name in ('Start', 'Update'):
        source = (ROOT/f'{name}-Madar.cmd').read_text()
        assert f'{name}-Madar.ps1' in source
        assert 'powershell.exe -NoProfile -ExecutionPolicy Bypass' in source
        assert 'exit /b %MADAR_EXIT%' in source
        assert 'docker' not in source.lower()
        assert 'n8n' not in source.lower()
