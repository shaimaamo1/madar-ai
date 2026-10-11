"""Single leased long poller in the app container. Durable offsets and no public ports."""
import asyncio
import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException

from . import db
from .telegram import configuration, process, store


def acquire(bot, tenant, owner):
    now = db.now()
    until = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat()
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('INSERT OR IGNORE INTO telegram_polling(bot_id,tenant_id) VALUES(?,?)', (bot, tenant))
        row = c.execute('SELECT * FROM telegram_polling WHERE bot_id=?', (bot,)).fetchone()
        if row['tenant_id'] != tenant or (row['owner'] != owner and row['lease_until'] > now):
            return None
        c.execute('UPDATE telegram_polling SET owner=?,lease_until=? WHERE bot_id=?', (owner, until, bot))
        return row['update_offset']


@db.serialized_conversation
async def consume(bot, tenant, owner, update):
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        lease = c.execute('SELECT * FROM telegram_polling WHERE bot_id=?', (bot,)).fetchone()
        if not lease or lease['owner'] != owner or lease['lease_until'] <= db.now():
            return None
        if type(update.get('update_id')) is not int or not 0 <= update['update_id'] < 2**63-1 or update['update_id'] < lease['update_offset']:
            return None
        try:
            result = await process(c, tenant, update)
        except HTTPException as error:
            if error.status_code != 400:
                raise
            # Malformed provider update: no message/CRM mutation occurs before validation.
            result = {'ignored': True}
            db.audit(c, tenant, 'telegram', 'telegram.invalid_update', bot, 'Malformed update ignored; content omitted')
        until = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat()
        c.execute("UPDATE telegram_polling SET update_offset=?,last_received=?,lease_until=?,error='' WHERE bot_id=? AND owner=?", (update['update_id'] + 1, db.now(), until, bot, owner))
        return result


def release(owner):
    with db.connection() as c:
        c.execute("UPDATE telegram_polling SET owner='',lease_until='' WHERE owner=?", (owner,))


async def cycle(owner):
    cfg = configuration()
    tenant = os.getenv('MADAR_INTEGRATION_TENANT_ID', '')
    if not tenant or not cfg.get('connected') or cfg.get('transport', 'polling') != 'polling' or not cfg.get('token'):
        return 2
    bot = cfg['token'].split(':')[0]
    offset = acquire(bot, tenant, owner)
    if offset is None:
        return 5
    async with httpx.AsyncClient(timeout=35, trust_env=False, follow_redirects=False) as client:
        response = await client.post('https://api.telegram.org/bot' + cfg['token'] + '/getUpdates',
            json={'offset': offset, 'timeout': 25, 'limit': 10, 'allowed_updates': ['message', 'callback_query']})
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError('Invalid provider response')
    if response.status_code != 200 or data.get('ok') is not True:
        code = data.get('error_code', response.status_code)
        with db.connection() as c:
            c.execute('UPDATE telegram_polling SET error=? WHERE bot_id=?', ('Telegram polling conflict' if code == 409 else 'Telegram polling unavailable', bot))
        if code in (401, 403, 404, 409):
            current = configuration()
            if current.get('token') == cfg['token']:
                current.update(connected=False, enabled=False, verified=False)
                store(current)
        parameters = data.get('parameters', {})
        delay = parameters.get('retry_after', 5) if isinstance(parameters, dict) else 5
        return min(max(delay if type(delay) is int else 5, 1), 60)
    with db.connection() as c:
        c.execute("UPDATE telegram_polling SET last_received=?,error='' WHERE bot_id=? AND owner=?", (db.now(), bot, owner))
    from .integrations import dispatch
    updates = data.get('result', [])
    if not isinstance(updates, list):
        raise ValueError('Invalid provider update list')
    for update in updates:
        current = configuration()
        if not current.get('connected') or current.get('token') != cfg['token']:
            break
        if not isinstance(update, dict):
            continue
        result = await consume(bot, tenant, owner, update)
        if result and current.get('enabled'):
            callback = update.get('callback_query')
            if callback and isinstance(callback.get('id'), str):
                from .telegram import provider
                try:
                    await provider(cfg['token'], 'answerCallbackQuery', {'callback_query_id': callback['id']})
                except HTTPException:
                    pass  # Selection was committed; optional UI acknowledgement must not replay it.
    # Also drain due retries after empty polls; no n8n availability dependency for replies.
    if configuration().get('enabled'):
        await dispatch(tenant, 'telegram')
    return 0.2


async def worker():
    owner = secrets.token_hex(16)
    try:
        while True:
            try:
                delay = await cycle(owner)
            except (httpx.HTTPError, HTTPException, ValueError, KeyError):
                # Never log token-bearing URLs, exception strings or provider payloads.
                delay = 5
                with db.connection() as c:
                    c.execute("UPDATE telegram_polling SET error='Telegram polling unavailable' WHERE owner=?", (owner,))
            await asyncio.sleep(delay)
    finally:
        release(owner)
