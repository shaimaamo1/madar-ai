"""Guided Telegram conversation using existing inventory, handoff and booking guards."""
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from . import db
from .availability import inventory_slots
from .domain import book, match_properties, human_requested
from .telegram_messages import text as safe_text, appointment_date, booking_message, timezone_label, property_recommendations


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
        if action['kind'] == 'agent':
            from .operations import set_handoff
            set_handoff(c, tenant, lead['id'], True, 'Customer requested an adviser', 'telegram-customer')
            return {'reply': 'تم إرسال طلبك إلى مستشارك العقاري. سيتابع معك، والردود الآلية متوقفة حتى يعيد المساعد.' if arabic else 'Your request has been sent to your property adviser. Automated replies are paused until the adviser releases the conversation.', 'buttons': [], 'matches': []}
        property_id = payload['property_id']
        prop = c.execute('SELECT * FROM properties WHERE id=? AND tenant_id=? AND status=?', (property_id, tenant, 'Available')).fetchone()
        if not prop:
            return {'reply': 'العقار لم يعد متاحاً. اطلب /properties للاطلاع على المخزون الحالي.' if arabic else 'This property is no longer available. Use /properties for current inventory.', 'buttons': [], 'matches': []}
        if action['kind'] == 'property':
            available = inventory_slots(c, tenant, lead['id'], property_id)
            zone = available.get('timezone') or cfg.get('timezone') or 'Africa/Cairo'
            buttons = [button(c, tenant, lead, bot, 'slot', {'property_id': property_id, **slot}, appointment_date(slot['start_at'], arabic, zone)) for slot in available['slots'][:6]]
            reply = (('اختر موعدًا مناسبًا لمعاينة ' if arabic else 'Choose a viewing time for ') + safe_text(prop['title'], arabic)) if buttons else ('لا توجد مواعيد متاحة حالياً. اطلب /agent للمساعدة.' if arabic else 'No viewing times are available. Use /agent for assistance.')
            if buttons:
                reply += '\n\n' + ('🕒 التوقيت: ' if arabic else '🕒 Timezone: ') + safe_text(timezone_label(available['slots'][0]['start_at'], zone), arabic)
            return {'reply': reply, 'buttons': buttons, 'matches': []}
        if action['kind'] == 'slot':
            return {'reply': booking_message(prop, payload['start_at'], arabic, cfg.get('timezone')),
                    'buttons': [button(c, tenant, lead, bot, 'confirm', payload, 'تأكيد الحجز' if arabic else 'Confirm booking')], 'matches': []}
        if action['kind'] == 'confirm':
            try:
                appointment = book(c, tenant, {'lead_id': lead['id'], 'property_id': property_id, 'agent_id': payload['agent_id'], 'start_at': payload['start_at']}, 'telegram-customer')
            except HTTPException:
                return {'reply': 'الموعد لم يعد متاحاً. اختر موعداً جديداً عبر /properties.' if arabic else 'This slot is no longer available. Choose a new time using /properties.', 'buttons': [], 'matches': []}
            return {'reply': booking_message(prop, appointment['start_at'], arabic, cfg.get('timezone'), reference=appointment['id']),
                    'buttons': [button(c, tenant, lead, bot, 'agent', {}, 'التواصل مع مستشار' if arabic else 'Contact an agent')], 'matches': []}
    command = text.split()[0].split('@')[0]
    if command == '/help':
        return {'reply': 'MADAR AI Assistant\n\n' + ('/properties — العقارات\n/appointments — مواعيدك\n/agent — مستشار بشري\n/subscribe — الموافقة على المتابعة\n/stop — إيقاف الرسائل' if arabic else '/properties — properties\n/appointments — your viewings\n/agent — human adviser\n/subscribe — allow follow-ups\n/stop — stop messages'), 'buttons': [], 'matches': []}
    if command in ('/appointments', '/status'):
        appointments = c.execute('SELECT a.id,a.start_at,a.status,p.title FROM appointments a JOIN properties p ON p.id=a.property_id AND p.tenant_id=a.tenant_id WHERE a.tenant_id=? AND a.lead_id=? ORDER BY a.start_at LIMIT 10', (tenant, lead['id'])).fetchall()
        blocks=[]
        for row in appointments:
            status = {'Booked':'محجوز','Completed':'مكتمل','Cancelled':'ملغى'}.get(row['status'], row['status']) if arabic else row['status']
            blocks.append('🏠 ' + safe_text(row['title'], arabic) + '\n' +
                          '📅 ' + appointment_date(row['start_at'], arabic, cfg.get('timezone'), include_year=True) + '\n' +
                          ('🕒 التوقيت: ' if arabic else '🕒 Timezone: ') + safe_text(timezone_label(row['start_at'], cfg.get('timezone')), arabic) + '\n' +
                          ('الحالة: ' if arabic else 'Status: ') + status)
        return {'reply': '\n\n'.join(blocks) if blocks else ('لا توجد معاينات مسجلة. استخدم /properties لاختيار عقار وموعد.' if arabic else 'No viewings recorded. Use /properties to choose a property and time.'), 'buttons': [], 'matches': []}
    if command == '/properties' or re.search(r'viewing|appointment|معاينة|معاينه', text, re.I):
        matches = match_properties(c, tenant, lead)
        return {'reply': property_recommendations(matches, cfg['currency'], arabic) if matches else ('لا توجد عقارات متاحة تطابق طلبك.' if arabic else 'No available inventory matches your requirements.'),
                'buttons': [button(c, tenant, lead, bot, 'property', {'property_id': p['id']}, ('معاينة: ' if arabic else 'View: ') + p['title']) for p in matches[:3]], 'matches': matches}
    return None
