import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, Response

from .db import connection, default_settings, now, uid
from .seed import seed_demo

hasher = PasswordHasher()
PRODUCTION = os.getenv('MADAR_ENV') == 'production'
DEMO = os.getenv('MADAR_DEMO_MODE', 'false' if PRODUCTION else 'true').lower() == 'true'
PUBLIC_URL = os.getenv('MADAR_PUBLIC_URL', 'http://localhost:8000').rstrip('/')
_rates = defaultdict(deque)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def limit(key, count=30, seconds=60):
    clock = time.monotonic()
    events = _rates[key]
    while events and events[0] < clock - seconds:
        events.popleft()
    if len(events) >= count:
        raise HTTPException(429, 'Please wait before trying again')
    events.append(clock)
    # Memory bound for anonymous clients. Single-process deployment only.
    if len(_rates) > 10000:
        for stale in list(_rates):
            if not _rates[stale] or _rates[stale][-1] < clock - seconds:
                del _rates[stale]


def login_session(c, user_id, response):
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
    c.execute('DELETE FROM sessions WHERE expires_at<?', (now(),))
    c.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(token), user_id, expires))
    response.set_cookie('madar_session', token, httponly=True, secure=PRODUCTION, samesite='strict', max_age=43200, path='/')


def current_user(request: Request):
    token = request.cookies.get('madar_session', '')
    with connection() as c:
        user = c.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1', (digest(token), now())).fetchone()
    if not user:
        raise HTTPException(401, 'Sign in to continue')
    return dict(user)


def admin(user):
    if user['role'] != 'admin':
        raise HTTPException(403, 'Administrator access required')


def bootstrap():
    if PRODUCTION and (DEMO or not PUBLIC_URL.startswith('https://')):
        raise RuntimeError('Production requires HTTPS and MADAR_DEMO_MODE=false')
    with connection() as c:
        if c.execute("SELECT 1 FROM tenants WHERE slug='madar'").fetchone():
            return
        password = os.getenv('MADAR_ADMIN_PASSWORD')
        if not password:
            if PRODUCTION:
                raise RuntimeError('Securely supply MADAR_ADMIN_PASSWORD before first production start')
            password = secrets.token_urlsafe(24)
            path = Path('var/initial-admin-password')
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(password)
        if len(password) < 12:
            raise RuntimeError('Administrator password must contain at least 12 characters')
        tenant, user = uid(), uid()
        import json
        c.execute('INSERT INTO tenants VALUES(?,?,?,?,?)', (tenant, 'madar', 'MADAR AI', json.dumps(default_settings('MADAR AI')), 0))
        c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)', (user, tenant, os.getenv('MADAR_ADMIN_EMAIL', 'admin@madar.local'), 'Workspace Owner', 'admin', hasher.hash(password), 1))


def demo_workspace(c, response):
    if not DEMO:
        raise HTTPException(404, 'Demonstration mode disabled')
    import json
    tenant, user = uid(), uid()
    c.execute('INSERT INTO tenants VALUES(?,?,?,?,?)', (tenant, 'demo-' + tenant[:10], 'Madar Estates', json.dumps(default_settings('Madar Estates')), 1))
    password = hasher.hash(secrets.token_urlsafe(32))
    c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)', (user, tenant, 'owner@demo.invalid', 'Demo Owner', 'admin', password, 1))
    seed_demo(c, tenant, user, password)
    login_session(c, user, response)
    return {'demo': True, 'tenant_id': tenant}


def check_origin(request):
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    # Cross-site browser mutations are rejected. Webhooks use their own signatures.
    origin = request.headers.get('origin')
    if origin and origin.rstrip('/') != PUBLIC_URL:
        if not PRODUCTION and origin in ('http://localhost:5173', 'http://127.0.0.1:5173', 'http://127.0.0.1:8000'):
            return
        raise HTTPException(403, 'Cross-site request rejected')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Cross-site request rejected')
