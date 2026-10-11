"""Guided Telegram conversation using existing inventory, handoff and booking guards."""
import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from . import db
from .availability import inventory_slots
from .domain import book, match_properties, human_requested


def button(c, tenant, lead, bot, kind, payload, title):
    identifier = db.uid()
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    c.execute('INSERT INTO telegram_actions VALUES(?,?,?,?,?,?,?,0)', (identifier, tenant, lead['id'], bot, kind, json.dumps(payload), expiry))
    return [{'text': title[:60], 'callback_data': 'act:' + identifier}]


def guided(c, tenant, lead, bot, text, callback, arabic):
    """Return a grounded action response, or None to use the common assistant."""
    control = c.execute('SELECT human_active FROM conversation_controls WHERE tenant_id=? AND lead_id=?', (tenant, lead['id'])).fetchone()
    if (control and control[0]) or lead['opted_out'] or human_requested(text):
        return None
    cfg = db.settings(c, tenant)
    if callback:
        action = c.execute('SELECT * FROM telegram_actions WHERE id=? AND tenant_id=? AND lead_id=? AND bot_id=?', (callback.removeprefix('act:'), tenant, lead['id'], bot)).fetchone()
        if not action or action['expires_at'] < db.now() or action['used']:
            return {'reply': 'الاختيار انتهت صلاحيته أو تم استخدامه. اطلب /properties من جديد.' if arabic else 'This selection expired or was used. Request /properties again.', 'buttons': [], 'matches': []}
        c.execute('UPDATE telegram_actions SET used=1 WHERE id=?', (action['id'],))
        payload = json.loads(action['payload'])
        property_id = payload['property_id']
        prop = c.execute('SELECT * FROM properties WHERE id=? AND tenant_id=? AND status=?', (property_id, tenant, 'Available')).fetchone()
        if not prop:
            return {'reply': 'العقار لم يعد متاحاً. اطلب /properties للاطلاع على المخزون الحالي.' if arabic else 'This property is no longer available. Use /properties for current inventory.', 'buttons': [], 'matches': []}
        if action['kind'] == 'property':
            available = inventory_slots(c, tenant, lead['id'], property_id)
            zone = ZoneInfo(available.get('timezone', cfg['timezone']))
            buttons = [button(c, tenant, lead, bot, 'slot', {'property_id': property_id, **slot}, datetime.fromisoformat(slot['start_at']).astimezone(zone).strftime('%Y-%m-%d %H:%M')) for slot in available['slots'][:6]]
            return {'reply': (('اختر موعد معاينة للعقار ' if arabic else 'Choose a viewing time for ') + prop['title'] + '\n' + cfg['timezone']) if buttons else ('لا توجد مواعيد متاحة حالياً. اطلب /agent للمساعدة.' if arabic else 'No viewing times are available. Use /agent for assistance.'), 'buttons': buttons, 'matches': []}
        if action['kind'] == 'slot':
            start = datetime.fromisoformat(payload['start_at']).astimezone(ZoneInfo(cfg['timezone'])).strftime('%Y-%m-%d %H:%M')
            return {'reply': ('هل تؤكد معاينة ' if arabic else 'Confirm viewing of ') + prop['title'] + ' — ' + start + ' (' + cfg['timezone'] + ')?\n' + ('لم يتم الحجز بعد.' if arabic else 'Not booked yet.'), 'buttons': [button(c, tenant, lead, bot, 'confirm', payload, 'تأكيد الحجز' if arabic else 'Confirm booking')], 'matches': []}
        if action['kind'] == 'confirm':
            try:
                appointment = book(c, tenant, {'lead_id': lead['id'], 'property_id': property_id, 'agent_id': payload['agent_id'], 'start_at': payload['start_at']}, 'telegram-customer')
            except HTTPException:
                return {'reply': 'الموعد لم يعد متاحاً. اختر موعداً جديداً عبر /properties.' if arabic else 'This slot is no longer available. Choose a new time using /properties.', 'buttons': [], 'matches': []}
            return {'reply': ('تم تأكيد المعاينة: ' if arabic else 'Viewing confirmed: ') + prop['title'] + ' — ' + datetime.fromisoformat(appointment['start_at']).astimezone(ZoneInfo(cfg['timezone'])).strftime('%Y-%m-%d %H:%M') + ' (' + cfg['timezone'] + ')', 'buttons': [], 'matches': []}
    command = text.split()[0].split('@')[0]
    if command == '/help':
        return {'reply': '/properties — العقارات\n/appointments — مواعيدك\n/agent — مستشار بشري\n/subscribe — الموافقة على المتابعة\n/stop — إيقاف الرسائل' if arabic else '/properties — properties\n/appointments — your viewings\n/agent — human adviser\n/subscribe — allow follow-ups\n/stop — stop messages', 'buttons': [], 'matches': []}
    if command in ('/appointments', '/status'):
        appointments = c.execute('SELECT start_at,status FROM appointments WHERE tenant_id=? AND lead_id=? ORDER BY start_at LIMIT 10', (tenant, lead['id'])).fetchall()
        lines = [(('محجوز' if row['status'] == 'Booked' else 'مكتمل' if row['status'] == 'Completed' else 'ملغى') if arabic else row['status']) + ': ' + row['start_at'] for row in appointments]
        return {'reply': '\n'.join(lines) if lines else ('لا توجد معاينات مسجلة. استخدم /properties لاختيار عقار وموعد.' if arabic else 'No viewings recorded. Use /properties to choose a property and time.'), 'buttons': [], 'matches': []}
    if command == '/properties' or re.search(r'viewing|appointment|معاينة|معاينه', text, re.I):
        matches = match_properties(c, tenant, lead)
        lines = [f"{p['title']} — {p['price']:,.0f} {cfg['currency']}, {p['location']}" for p in matches[:3]]
        return {'reply': ('العقارات المتاحة حسب تفضيلاتك:\n' if arabic else 'Available properties for your preferences:\n') + '\n'.join(lines) if lines else ('لا توجد عقارات متاحة تطابق طلبك.' if arabic else 'No available inventory matches your requirements.'),
                'buttons': [button(c, tenant, lead, bot, 'property', {'property_id': p['id']}, ('معاينة: ' if arabic else 'View: ') + p['title']) for p in matches[:3]], 'matches': matches}
    return None
