"""SQLite storage. Every business query is scoped by tenant_id."""
import json
import os
import sqlite3
import uuid
import asyncio
from functools import wraps
from weakref import WeakKeyDictionary
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv('MADAR_DB_PATH', 'var/madar.sqlite3'))
_write_locks = WeakKeyDictionary()


def serialized_conversation(function):
    """Avoid blocking the event loop on competing SQLite writers during model calls."""
    @wraps(function)
    async def wrapped(*args, **kwargs):
        loop = asyncio.get_running_loop()
        lock = _write_locks.setdefault(loop, asyncio.Lock())
        async with lock:
            return await function(*args, **kwargs)
    return wrapped


def uid():
    return uuid.uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate():
    with connection() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript(Path(__file__).with_name('schema.sql').read_text())


def audit(c, tenant, actor, action, entity, detail=''):
    c.execute('INSERT INTO activities VALUES(?,?,?,?,?,?,?)',
              (uid(), tenant, actor, action, entity, detail, now()))


def settings(c, tenant):
    return json.loads(c.execute('SELECT settings FROM tenants WHERE id=?', (tenant,)).fetchone()[0])


def default_settings(name):
    return {'company_name': name, 'brand_color': '#D8BE83', 'logo_url': '', 'currency': 'EGP',
            'language': 'en', 'timezone': 'Africa/Cairo', 'business_start': 9, 'business_end': 18,
            'stages': ['New', 'Qualified', 'Viewing', 'Negotiation', 'Won', 'Lost'],
            'assistant_name': 'Madar', 'personality': 'Helpful, concise, honest property adviser',
            'followup_hours': 24, 'company_details': '', 'onboarding_complete': False}
