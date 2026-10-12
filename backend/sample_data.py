"""Explicit, transactional fictional portfolio copies; no provider/automation calls.

The isolated seeder runs in memory. Only its tracked business rows cross into the
real tenant; credentials, settings, contacts, sessions and outbox never do.
"""
from contextlib import closing
import json
import sqlite3
from pathlib import Path

from fastapi import HTTPException

from . import db
from .seed import seed_demo, TABLES

LABEL = 'Sample / Fictional'
VERSION = 'egypt-portfolio-v1'
ORDER = ('users', 'properties', 'leads', 'activities', 'appointments', 'tasks', 'messages', 'conversation_controls')
REFERENCES = {
    'leads': [('messages','lead_id'), ('tasks','lead_id'), ('appointments','lead_id'),
              ('deals','lead_id'), ('outbox','lead_id'), ('conversation_controls','lead_id'),
              ('consent_events','lead_id'), ('adviser_cases','lead_id'),
              ('enterprise_artifacts','lead_id'), ('chat_sessions','lead_id'),
              ('telegram_actions','lead_id'), ('telegram_contacts','lead_id'), ('activities','entity_id')],
    'properties': [('appointments','property_id'), ('deals','property_id'), ('activities','entity_id')],
    'appointments': [('activities','entity_id')],
    'tasks': [('activities','entity_id')],
    'users': [('appointments','agent_id'), ('leads','assigned_to'), ('adviser_cases','agent_id'),
              ('activities','actor'), ('sessions','user_id')],
}
KEYS = {'conversation_controls': 'lead_id', 'telegram_contacts': 'lead_id', 'chat_sessions':'token_hash', 'sessions':'token_hash'}


def require_real(c, tenant):
    row = c.execute('SELECT slug,demo FROM tenants WHERE id=?', (tenant,)).fetchone()
    if not row or row['slug'] != 'madar' or row['demo']:
        raise HTTPException(403, 'Sample business data is available only in the real madar workspace')


def owned(c, tenant):
    return {table: {r[0] for r in c.execute('SELECT record_id FROM sample_records WHERE tenant_id=? AND table_name=?', (tenant, table))} for table in TABLES}


def is_sample(c, tenant, table, identifier):
    return bool(c.execute('SELECT 1 FROM sample_records WHERE tenant_id=? AND table_name=? AND record_id=?', (tenant, table, identifier)).fetchone())


def dependencies(c, tenant):
    records = owned(c, tenant)
    if not any(records.values()):
        return {}
    result = {}
    for parent, children in REFERENCES.items():
        for table, field in children:
            # Inspect references globally: malformed legacy cross-tenant FKs
            # must never make a cascade delete someone else's business rows.
            key = KEYS.get(table, 'id')
            count = c.execute(f"""SELECT COUNT(*) FROM {table} child
                JOIN sample_records parent ON parent.record_id=child.{field}
                AND parent.tenant_id=? AND parent.table_name=?
                WHERE NOT EXISTS (SELECT 1 FROM sample_records tracked
                    WHERE tracked.tenant_id=? AND tracked.table_name=?
                    AND tracked.record_id=child.{key})""", (tenant, parent, tenant, table)).fetchone()[0]
            if count:
                result[table] = result.get(table, 0) + count
    # A pending confirmation is also a dependency, before the appointment exists.
    properties = records['properties']
    for row in c.execute('SELECT payload FROM telegram_actions WHERE tenant_id=? AND used=0 AND expires_at>?', (tenant, db.now())):
        payload = json.loads(row[0])
        if payload.get('property_id') in properties:
            result['pending_telegram_actions'] = result.get('pending_telegram_actions', 0) + 1
    return result


def status(c, tenant):
    records = owned(c, tenant)
    counts = {table: c.execute(f'SELECT COUNT(*) FROM {table} r JOIN sample_records s ON s.tenant_id=r.tenant_id AND s.record_id=r.{KEYS.get(table,"id")} AND s.table_name=? WHERE r.tenant_id=?', (table, tenant)).fetchone()[0] for table, ids in records.items() if ids}
    return {'loaded': bool(c.execute('SELECT 1 FROM sample_datasets WHERE tenant_id=?', (tenant,)).fetchone()),
            'label': LABEL, 'counts': counts, 'removal_dependencies': dependencies(c, tenant)}


def load(c, tenant, actor):
    require_real(c, tenant)
    if c.execute('SELECT 1 FROM sample_datasets WHERE tenant_id=?', (tenant,)).fetchone():
        return status(c, tenant)  # Never restore/overwrite records changed after import.
    stamp = db.now()
    with closing(sqlite3.connect(':memory:')) as source:
        source.row_factory = sqlite3.Row
        source.execute('PRAGMA foreign_keys=ON')
        source.executescript(Path(__file__).with_name('schema.sql').read_text())
        source.execute('INSERT INTO tenants VALUES(?,?,?,?,?)', ('source', 'demo-source', 'Sample portfolio', json.dumps(db.settings(c, tenant)), 1))
        source.execute('INSERT INTO demo_datasets VALUES(?,?,?)', ('source', VERSION, stamp))
        seed_demo(source, 'source', 'unused', '!sample-no-login')
        generated = {table: [dict(r) for r in source.execute(f'SELECT * FROM {table} WHERE tenant_id=?', ('source',))] for table in ORDER}
    # Explicit map preserves every FK without copying any external identity.
    ids = {r['id']: r['id'].replace('demo-', 'sample-', 1).replace('-source-', '-' + tenant + '-') for rows in generated.values() for r in rows if 'id' in r}
    c.execute('INSERT INTO sample_datasets VALUES(?,?,?)', (tenant, VERSION, stamp))
    for table in ORDER:
        for original in generated[table]:
            row = {key: ids.get(value, value) if isinstance(value, str) else value for key, value in original.items()}
            row['tenant_id'] = tenant
            if table == 'users':
                row.update(active=0, password_hash='!sample-no-login', email=row['email'].replace('@demo.invalid','@sample.invalid'), name=LABEL + ' · ' + row['name'])
            if table == 'leads':
                row.update(phone='', email=row['email'].replace('@demo.invalid','@sample.invalid'), external_id=row['external_id'].replace('sandbox:demo-', 'sandbox:sample-'), name=LABEL + ' · ' + row['name'])
            if table == 'messages':
                row['body'] = LABEL + ' — ' + row['body']
                row['external_id'] = row['external_id'].replace('sandbox:demo-', 'sandbox:sample-')
            for key in ('description', 'notes', 'detail', 'reason', 'title'):
                if key in row and not (table == 'properties' and key == 'title'):
                    row[key] = LABEL + ' — ' + row[key]
            row_key = row[KEYS.get(table, 'id')]
            # Plain INSERT: collisions abort the entire import, never adopt a real row.
            c.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", list(row.values()))
            c.execute('INSERT INTO sample_records VALUES(?,?,?)', (tenant, table, row_key))
    db.audit(c, tenant, actor, 'sample.imported', tenant, LABEL + '; no delivery or calendar side effects')
    return status(c, tenant)


def remove(c, tenant, actor):
    require_real(c, tenant)
    blocked = dependencies(c, tenant)
    if blocked:
        raise HTTPException(409, 'Sample removal blocked: real records or pending Telegram selections depend on sample data. Keep the inventory or resolve dependencies first.')
    records = owned(c, tenant)
    for table in TABLES:
        for identifier in records[table]:
            c.execute(f'DELETE FROM {table} WHERE tenant_id=? AND {KEYS.get(table,"id")}=?', (tenant, identifier))
    c.execute('DELETE FROM sample_records WHERE tenant_id=?', (tenant,))
    c.execute('DELETE FROM sample_datasets WHERE tenant_id=?', (tenant,))
    db.audit(c, tenant, actor, 'sample.removed', tenant, 'Only tracked sample records removed')
    return status(c, tenant)
