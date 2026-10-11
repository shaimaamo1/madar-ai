"""Telegram setup and private configuration. Provider secrets never leave the server."""
import json
import logging
import os
import re
import secrets
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import Field, SecretStr

from . import db
from .models import Model
from .security import admin, current_user, limit

router = APIRouter()


class TelegramLogFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r'(?:https://api\.telegram\.org)?/bot[^/\s\"\']+', '/bot[REDACTED]', record.getMessage())
        record.args = ()
        return True


def protect_provider_logs():
    # httpx logs token-bearing Bot API URLs even at INFO verbosity.
    for name in ('httpx', 'httpcore.connection', 'httpcore.http11', 'httpcore.http2', 'httpcore.proxy'):
        logger = logging.getLogger(name)
        if not any(isinstance(item, TelegramLogFilter) for item in logger.filters):
            logger.addFilter(TelegramLogFilter())


protect_provider_logs()


def private_path():
    return db.DB_PATH.parent / 'telegram-private.json'


def configuration():
    path = private_path()
    if path.exists():
        # Container storage must be private, including files restored from backups.
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise HTTPException(503, 'Telegram private configuration permissions need repair')
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                raise ValueError()
        except (OSError, ValueError):
            raise HTTPException(503, 'Telegram private configuration cannot be read safely')
        if data.get('tenant_id') != os.getenv('MADAR_INTEGRATION_TENANT_ID'):
            return {}
        return data
    return {'token': os.getenv('TELEGRAM_BOT_TOKEN', ''), 'secret': os.getenv('TELEGRAM_WEBHOOK_SECRET', ''),
            'enabled': os.getenv('MADAR_ALLOW_TELEGRAM_SEND', 'false') == 'true'}


def store(data):
    data['revision'] = secrets.token_hex(16)
    path = private_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.telegram-', dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def assert_current(data):
    current = configuration()
    if current.get('revision') != data.get('revision') or current.get('token') != data.get('token'):
        raise HTTPException(409, 'Telegram configuration changed; reload and retry')


def operator(user):
    admin(user)
    with db.connection() as c:
        demo = c.execute('SELECT demo FROM tenants WHERE id=?', (user['tenant_id'],)).fetchone()[0]
    if demo or user['tenant_id'] != os.getenv('MADAR_INTEGRATION_TENANT_ID'):
        raise HTTPException(403, 'Telegram setup requires the bound non-demo administrator workspace')
    limit('telegram-setup:' + user['id'], 20)


def connection_error(data):
    if not data.get('token'):
        return ''
    with db.connection() as c:
        row = c.execute('SELECT error FROM telegram_polling WHERE bot_id=?', (data['token'].split(':')[0],)).fetchone()
    return row[0] if row else ''


def polling_status(data):
    with db.connection() as c:
        row = c.execute('SELECT last_received,lease_until,error FROM telegram_polling WHERE bot_id=?', (str(data.get('token','')).split(':')[0],)).fetchone()
    active = bool(data.get('connected') and row and row['last_received'] and row['lease_until'] > db.now() and not row['error'])
    return {'polling_active': active, 'last_poll_at': row['last_received'] if row else ''}


def status(data):
    polling = polling_status(data)
    return {**polling, 'configured': bool(data.get('token') and data.get('secret')), 'verified': bool(data.get('verified')),
            'enabled': bool(data.get('enabled')), 'registered': bool(data.get('registered')),
            'public_origin': data.get('public_origin', ''), 'bot_username': data.get('bot_username', ''),
            'mode': 'model-assisted' if os.getenv('MADAR_AI_API_KEY') and os.getenv('MADAR_ALLOW_MODEL_USAGE') == 'true' else 'deterministic',
            'connected': bool(data.get('connected')), 'transport': data.get('transport', 'polling'), 'connection_error': connection_error(data), 'webhook_path': '/webhooks/telegram'}


async def provider(token, method, payload=None):
    if not token:
        raise HTTPException(422, 'Telegram bot token is required')
    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False, follow_redirects=False) as client:
            response = await client.post('https://api.telegram.org/bot' + token + '/' + method, json=payload or {})
        data = response.json()
        if not isinstance(data, dict) or response.status_code != 200 or data.get('ok') is not True:
            raise HTTPException(502, 'Telegram verification or configuration failed; provider details omitted')
        return data.get('result', {})
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'Telegram unreachable; credentials and provider details omitted')


class Configuration(Model):
    token: SecretStr | None = None
    public_origin: str = Field(default='', max_length=300)


def https_origin(value):
    if not value:
        return ''
    try:
        parts = urlsplit(value)
        hostname = parts.hostname or ''
        if (parts.scheme != 'https' or parts.username or parts.password or parts.query or parts.fragment
                or parts.path not in ('', '/') or parts.port not in (None, 443, 8443)
                or not re.fullmatch(r'(?=.{1,253}$)[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,63}', hostname)
                or hostname.lower().endswith(('.localhost', '.local', '.internal'))):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'Use a public HTTPS origin without a path, query or credentials')
    return value.rstrip('/')


@router.get('/api/telegram/setup')
def get_setup(user=Depends(current_user)):
    operator(user)
    return status(configuration())


@router.put('/api/telegram/setup')
def save_setup(data: Configuration, user=Depends(current_user)):
    operator(user)
    origin = https_origin(data.public_origin)
    cfg = configuration()
    if data.token is not None:
        token = data.token.get_secret_value().strip()
        if not re.fullmatch(r'\d{5,20}:[A-Za-z0-9_-]{20,100}', token):
            raise HTTPException(422, 'Invalid Telegram bot token format')
        if cfg.get('token') and cfg['token'] != token:
            raise HTTPException(409, 'Disconnect the existing bot before replacing its token')
        cfg.update(token=token)
    if not cfg.get('token'):
        raise HTTPException(422, 'Telegram bot token is required')
    cfg.setdefault('secret', secrets.token_urlsafe(32))
    if cfg.get('public_origin', '') != origin:
        cfg.update(registered=False)
    cfg.update(public_origin=origin, tenant_id=user['tenant_id'])
    store(cfg)
    with db.connection() as c:
        db.audit(c, user['tenant_id'], user['id'], 'telegram.configured', 'telegram', 'Secret retained privately; no public exposure performed')
    return status(cfg)


@router.post('/api/telegram/test')
async def test_connection(user=Depends(current_user)):
    operator(user)
    cfg = configuration()
    identity = await provider(cfg.get('token'), 'getMe')
    assert_current(cfg)
    if not isinstance(identity, dict) or identity.get('is_bot') is not True:
        raise HTTPException(502, 'Telegram identity is not a bot')
    cfg.update(verified=True, bot_username=identity.get('username', ''), tenant_id=user['tenant_id'])
    store(cfg)
    return status(cfg)


class Authorization(Model):
    authorized: bool = False


@router.post('/api/telegram/register-webhook')
async def register(data: Authorization, user=Depends(current_user)):
    operator(user)
    cfg = configuration()
    if not data.authorized or not cfg.get('verified') or not cfg.get('public_origin'):
        raise HTTPException(422, 'Explicit authorization, verified bot and public HTTPS origin required')
    await provider(cfg['token'], 'setWebhook', {'url': https_origin(cfg['public_origin']) + '/webhooks/telegram',
                   'secret_token': cfg['secret'], 'allowed_updates': ['message', 'callback_query'], 'max_connections': 10, 'drop_pending_updates': False})
    assert_current(cfg)
    cfg.update(registered=True, connected=False, transport='webhook')
    store(cfg)
    with db.connection() as c:
        db.audit(c, user['tenant_id'], user['id'], 'telegram.webhook_registered', 'telegram')
    return status(cfg)


@router.put('/api/telegram/delivery')
def delivery(data: Authorization, user=Depends(current_user)):
    operator(user)
    cfg = configuration()
    if data.authorized and not cfg.get('verified'):
        raise HTTPException(422, 'Verify the Telegram bot before enabling delivery')
    cfg.update(enabled=data.authorized, tenant_id=user['tenant_id'])
    store(cfg)
    with db.connection() as c:
        db.audit(c, user['tenant_id'], user['id'], 'telegram.delivery_enabled' if data.authorized else 'telegram.delivery_disabled', 'telegram')
    return status(cfg)


@router.post('/api/telegram/disconnect')
async def disconnect(data: Authorization, user=Depends(current_user)):
    operator(user)
    if not data.authorized:
        raise HTTPException(422, 'Explicit authorization required')
    cfg = configuration()
    # Persist the deny gate BEFORE the external call; failed disconnection cannot send.
    cfg.update(enabled=False, connected=False, tenant_id=user['tenant_id']);store(cfg)
    if cfg.get('token') and cfg.get('registered'):
        await provider(cfg['token'], 'deleteWebhook', {'drop_pending_updates': False})
    assert_current(cfg)
    store({'tenant_id': user['tenant_id'], 'enabled': False})
    return status(configuration())


async def process(c, tenant, data, fictional=False):
    from .assistant import respond
    from .domain import create_lead
    from .main import queue_message
    if not isinstance(data, dict) or type(data.get('update_id')) is not int or not 0 <= data['update_id'] < 2**63:
        raise HTTPException(400, 'Invalid Telegram update')
    callback = data.get('callback_query')
    callback_data = ''
    if isinstance(callback, dict):
        if not isinstance(callback.get('message'), dict) or not isinstance(callback.get('data'), str) or not re.fullmatch(r'act:[a-f0-9]{32}', callback['data']):
            return {'ignored': True}
        callback_data = callback['data']
        message = {**callback['message'], 'from': callback.get('from', {}), 'text': '/selection'}
    else:
        message = data.get('message')
    if not isinstance(message, dict):
        return {'ignored': True}
    chat = message.get('chat', {})
    if not isinstance(chat, dict) or chat.get('type') != 'private' or not isinstance(message.get('text'), str):
        return {'ignored': True}
    chat_id = chat.get('id')
    if type(chat_id) is not int or not 0 < chat_id < 2**63 or not 0 < len(message['text']) <= 4000:
        raise HTTPException(400, 'Invalid Telegram message')
    sender = message.get('from', {})
    if not isinstance(sender, dict) or ('id' in sender and sender['id'] != chat_id):
        raise HTTPException(400, 'Invalid Telegram sender')
    cfg = configuration() if not fictional else {}
    bot_id = str(cfg.get('token', '')).split(':')[0] or 'legacy'
    event = ('sandbox:' if fictional else bot_id + ':') + str(data['update_id'])
    contact = ('sandbox:telegram:' if fictional else '') + str(chat_id)
    inserted = c.execute('INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?)', (db.uid(), tenant, 'telegram', event, db.now()))
    if not inserted.rowcount:
        return {'duplicate': True, 'sandbox': fictional}
    text = message['text']
    arabic = bool(re.search('[\u0600-\u06ff]', text)) or (text.startswith('/') and str(sender.get('language_code', '')).startswith('ar'))
    commands = {'/start': 'أهلاً' if arabic else 'Hello', '/stop': 'وقف الرسائل' if arabic else 'stop',
                '/subscribe': 'موافق على رسائل المتابعة' if arabic else 'I consent to follow-up', '/handoff': 'مستشار' if arabic else 'human', '/agent': 'مستشار' if arabic else 'human'}
    normalized = commands.get(text.split()[0].split('@')[0], text)
    name = str(sender.get('first_name') or 'Telegram visitor')[:160]
    lead, _ = create_lead(c, tenant, {'name': name, 'source': 'telegram', 'external_id': contact})
    remembered = c.execute('SELECT language FROM telegram_contacts WHERE tenant_id=? AND lead_id=?', (tenant, lead['id'])).fetchone()
    if callback_data or text.startswith('/') or not re.search('[a-zA-Z\u0600-\u06ff]', text):
        arabic = (remembered[0] == 'ar') if remembered else str(sender.get('language_code', '')).startswith('ar')
    c.execute('INSERT INTO telegram_contacts VALUES(?,?,?) ON CONFLICT(tenant_id,lead_id) DO UPDATE SET language=excluded.language', (tenant, lead['id'], 'ar' if arabic else 'en'))
    commands.update({'/start': 'أهلاً' if arabic else 'Hello', '/agent': 'مستشار' if arabic else 'human', '/handoff': 'مستشار' if arabic else 'human', '/stop': 'وقف الرسائل' if arabic else 'stop', '/subscribe': 'موافق على رسائل المتابعة' if arabic else 'I consent to follow-up'})
    normalized = commands.get(text.split()[0].split('@')[0], text)
    from .telegram_conversation import guided, button
    from .domain import qualify
    if not callback_data and re.search(r'viewing|appointment|معاينة|معاينه', normalized, re.I):
        lead = qualify(c, tenant, lead, normalized)
    result = guided(c, tenant, lead, bot_id, normalized, callback_data, arabic)
    if result is None:
        result = await respond(c, tenant, lead, normalized, 'telegram', event, allow_model=not fictional, reply_language='ar' if arabic else 'en')
        result['buttons'] = [button(c, tenant, lead, bot_id, 'property', {'property_id': p['id']}, ('معاينة: ' if arabic else 'View: ') + p['title']) for p in result['matches'][:3]] if result['reply'] else []
    else:
        result['mode'] = 'rules'
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)', (db.uid(), tenant, lead['id'], 'inbound', 'telegram', text, event, db.now()))
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)', (db.uid(), tenant, lead['id'], 'outbound', 'telegram', result['reply'], '', db.now()))
        db.audit(c, tenant, 'telegram', 'telegram.guided_reply', lead['id'], 'deterministic')
    c.execute("UPDATE messages SET body=? WHERE tenant_id=? AND channel='telegram' AND direction='inbound' AND external_id=?", (text, tenant, event))
    reply = result['reply']
    if reply and result['mode'].startswith('rules'):
        reply = ('[مساعد آلي بقواعد محددة]\n' if arabic else '[Deterministic assistant]\n') + reply
        c.execute("UPDATE messages SET body=? WHERE id=(SELECT id FROM messages WHERE tenant_id=? AND lead_id=? AND direction='outbound' ORDER BY created_at DESC LIMIT 1)", (reply, tenant, lead['id']))
    if reply and not fictional:
        control = c.execute('SELECT human_active FROM conversation_controls WHERE tenant_id=? AND lead_id=?', (tenant, lead['id'])).fetchone()
        prefix = 'handoff-ack:' if control and control[0] else 'event:telegram:'
        queue_message(c, tenant, lead['id'], 'telegram', reply, prefix + event)
        markup = {'inline_keyboard': result.get('buttons', [])} if result.get('buttons') else {'keyboard': [[{'text':'/properties'}, {'text':'/appointments'}], [{'text':'/agent'}, {'text':'/help'}]], 'resize_keyboard': True}
        c.execute('UPDATE outbox SET template=? WHERE tenant_id=? AND dedupe_key=?', (json.dumps(markup), tenant, prefix + event))
    return {'accepted': True, 'duplicate': False, 'sandbox': fictional, 'lead_id': lead['id'],
            'reply': reply, 'mode': result['mode'], 'matches': result['matches'], 'buttons': result.get('buttons', [])}


async def receive(request: Request, background: BackgroundTasks):
    from .integrations import dispatch, integration_tenant
    cfg = configuration()
    expected = cfg.get('secret', '')
    if not expected or not secrets.compare_digest(request.headers.get('x-telegram-bot-api-secret-token', ''), expected):
        raise HTTPException(401, 'Webhook secret required')
    raw = await request.body()
    if len(raw) > 65536:
        raise HTTPException(413, 'Telegram update too large')
    try:
        data = json.loads(raw)
    except ValueError:
        raise HTTPException(400, 'Invalid Telegram JSON')
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        tenant = integration_tenant(c)
        result = await process(c, tenant, data)
    if result.get('accepted') and cfg.get('enabled'):
        background.add_task(dispatch, tenant, 'telegram')
    # Provider webhook receives only acknowledgement; CRM data stays private.
    return {k: v for k, v in result.items() if k in ('accepted', 'duplicate', 'ignored')}


class FictionalUpdate(Model):
    update_id: int = Field(ge=0, lt=2**63)
    chat_id: int = Field(default=101, gt=0, lt=2**63)
    text: str = Field(min_length=1, max_length=4000)
    language: str = Field(default='en', pattern='^(ar|en)$')
    callback_data: str = Field(default='', pattern='^(?:act:[a-f0-9]{32})?$')


@router.post('/api/sandbox/telegram')
@db.serialized_conversation
async def demo(data: FictionalUpdate, user=Depends(current_user)):
    admin(user)
    with db.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute('SELECT demo FROM tenants WHERE id=?', (user['tenant_id'],)).fetchone()[0]:
            raise HTTPException(403, 'Telegram sandbox requires an isolated fictional demo workspace')
        update = {'update_id': data.update_id, 'message': {'text': data.text,
                   'chat': {'id': data.chat_id, 'type': 'private'}, 'from': {'id': data.chat_id, 'first_name': 'Fictional Telegram customer', 'language_code': data.language}}}
        if data.callback_data:
            update['callback_query'] = {'message': update.pop('message'), 'from': {'id': data.chat_id, 'language_code': data.language}, 'data': data.callback_data}
        return await process(c, user['tenant_id'], update, fictional=True)

class ConnectInput(Model):
    replace_webhook: bool = False


@router.post('/api/telegram/connect')
async def connect(data: ConnectInput, user=Depends(current_user)):
    operator(user)
    await test_connection(user)
    cfg = configuration()
    info = await provider(cfg['token'], 'getWebhookInfo')
    assert_current(cfg)
    if not isinstance(info, dict):
        raise HTTPException(502, 'Telegram verification or configuration failed; provider details omitted')
    if info.get('url'):
        if not data.replace_webhook:
            raise HTTPException(409, 'This bot has a webhook; authorize replacing it before polling')
        await provider(cfg['token'], 'deleteWebhook', {'drop_pending_updates': False})
    assert_current(cfg)
    cfg.update(connected=True, registered=False, transport='polling', tenant_id=user['tenant_id'])
    store(cfg)
    with db.connection() as c:
        c.execute("UPDATE telegram_polling SET error='' WHERE bot_id=?", (cfg['token'].split(':')[0],))
        db.audit(c, user['tenant_id'], user['id'], 'telegram.polling_connected', 'telegram')
    return status(cfg)
