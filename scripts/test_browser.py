#!/usr/bin/env python3
"""Run browser regressions against disposable servers, never an owner database.

Requires installed backend development dependencies, frontend/node_modules,
a production frontend build, and Chromium (MADAR_CHROMIUM_PATH if needed).
Each file gets a fresh database/server so production demo-login rate limits stay
intact. Python/Node are developer test tools, not Windows launcher dependencies.
"""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent


def main():
    node = shutil.which('node')
    cli = ROOT / 'frontend/node_modules/@playwright/test/cli.js'
    if not node or not cli.exists() or not (ROOT / 'frontend/dist/index.html').exists():
        raise SystemExit('Install development dependencies and run the frontend production build first.')
    paths = sorted((ROOT / 'frontend/e2e').glob('*.spec.ts'))
    if sys.argv[1:]:
        paths = [path for path in paths if path.stem.removesuffix('.spec') in sys.argv[1:]]
        if not paths:
            raise SystemExit('No matching browser test files.')
    results = []
    for path in paths:
        with tempfile.TemporaryDirectory(prefix='madar-browser-fixture-') as folder:
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
            origin = f'http://127.0.0.1:{port}'
            environment = {**os.environ, 'MADAR_DB_PATH':str(Path(folder)/'fixture.sqlite3'),
                'MADAR_ADMIN_PASSWORD':'TestOnlyPassword123!', 'MADAR_ADMIN_EMAIL':'admin@madar.local',
                'MADAR_ENV':'development', 'MADAR_DEMO_MODE':'true', 'N8N_ENABLED':'false',
                'MADAR_TELEGRAM_POLL_WORKER':'false', 'MADAR_ALLOW_EXTERNAL_SEND':'false',
                'MADAR_ALLOW_TELEGRAM_SEND':'false', 'MADAR_ALLOW_MODEL_USAGE':'false',
                'MADAR_INTEGRATION_WORKSPACE':'madar', 'MADAR_PUBLIC_URL':origin,
                'MADAR_SAMPLE_E2E_FIXTURE':'true', 'MADAR_E2E_BASE_URL':origin,
                'MADAR_SAMPLE_TELEGRAM_E2E_FIXTURE':'true',
                'MADAR_E2E_PREVIEW_DIR':str(Path(folder)/'previews')}
            for key in ('TELEGRAM_BOT_TOKEN','TELEGRAM_WEBHOOK_SECRET','MADAR_AI_API_KEY',
                        'MADAR_INTEGRATION_TENANT_ID','N8N_API_KEY','MADAR_BRIDGE_TOKEN'):
                environment.pop(key, None)
            environment['TELEGRAM_WEBHOOK_SECRET'] = 'fictional-browser-sample-secret'
            server = subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app',
                '--host','127.0.0.1','--port',str(port),'--log-level','warning'],
                cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                ready = False
                for attempt in range(100):
                    if server.poll() is not None:
                        break
                    try:
                        with urlopen(origin+'/api/health', timeout=1) as response:
                            ready = response.status == 200
                        if ready:
                            break
                    except OSError:
                        time.sleep(.1)
                if not ready:
                    raise RuntimeError('Disposable fixture startup failed; no customer database was used.')
                print('\nBrowser fixture: ' + path.name, flush=True)
                completed = subprocess.run([node,str(cli),'test','e2e/'+path.name],
                    cwd=ROOT/'frontend', env=environment)
                results.append((path.name, completed.returncode))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
    for name, code in results:
        print(('PASS' if code == 0 else 'FAIL') + ' ' + name)
    return int(any(code for name, code in results))


if __name__ == '__main__':
    raise SystemExit(main())
