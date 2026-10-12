import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .db import audit, now, settings, uid


def record(row):
    d = dict(row)
    if d.get('id', '').startswith('sample-'):
        d['sample'] = True
        d['sample_label'] = 'Sample / Fictional'
        if 'size' in d and 'price' in d:
            d['reference'] = 'SAMPLE-EG-' + d['id'].rsplit('-', 1)[-1]
    if 'amenities' in d:
        d['amenities'] = json.loads(d['amenities'])
    if 'size' in d and 'price' in d and d.get('id', '').startswith('demo-property-'):
        d['demo'] = True
        d['reference'] = 'DEMO-EG-' + d['id'].rsplit('-', 1)[-1]
    return d


def require(c, table, tenant, entity):
    # Table identifiers are internal constants only.
    row = c.execute(f'SELECT * FROM {table} WHERE tenant_id=? AND id=?', (tenant, entity)).fetchone()
    if not row:
        raise HTTPException(404, 'Record not found')
    return record(row)


def score(lead):
    return min(100, (25 if lead['budget'] else 0) + (20 if lead['location'] else 0)
               + (15 if lead['property_type'] else 0) + (15 if lead['phone'] or lead['email'] else 0)
               + (10 if lead['bedrooms'] else 0) + (15 if lead['consent'] else 0))


def create_lead(c, tenant, data, actor='system'):
    data = dict(data)
    data['phone'] = re.sub(r'\D', '', data.get('phone', ''))
    data['email'] = data.get('email', '').strip().lower()
    existing = []
    for key in ('phone', 'email', 'external_id'):
        if data.get(key):
            query = f'SELECT id FROM leads WHERE tenant_id=? AND {key}=?'
            args = [tenant, data[key]]
            if key == 'external_id':
                query += ' AND source=?'
                args.append(data.get('source', 'website'))
            found = c.execute(query, args).fetchone()
            if found:
                existing.append(found[0])
    if len(set(existing)) > 1:
        raise HTTPException(409, 'Contact identities belong to different leads; review before merging')
    if existing:
        return require(c, 'leads', tenant, existing[0]), False
    agents = c.execute("SELECT u.id,COUNT(l.id) AS load FROM users u LEFT JOIN leads l ON l.assigned_to=u.id AND l.tenant_id=u.tenant_id AND l.stage NOT IN ('Won','Lost') WHERE u.tenant_id=? AND u.active=1 AND NOT EXISTS (SELECT 1 FROM sample_records sr WHERE sr.tenant_id=u.tenant_id AND sr.table_name='users' AND sr.record_id=u.id) GROUP BY u.id ORDER BY load,u.id", (tenant,)).fetchall()
    lead = {'id': uid(), 'tenant_id': tenant, 'name': 'Website visitor', 'phone': '', 'email': '',
            'source': 'website', 'external_id': '', 'stage': 'New', 'budget': 0, 'location': '',
            'property_type': '', 'intent': 'buy', 'bedrooms': 0, 'min_size': 0, 'amenities': [],
            'score': 0, 'assigned_to': agents[0]['id'] if agents else '', 'consent': False,
            'opted_out': False, 'created_at': now(), 'updated_at': now()}
    lead.update(data)
    lead['score'] = score(lead)
    values = dict(lead, amenities=json.dumps(lead['amenities']))
    c.execute(f"INSERT INTO leads ({','.join(values)}) VALUES ({','.join('?' for _ in values)})", list(values.values()))
    due = (datetime.now(timezone.utc) + timedelta(hours=settings(c, tenant)['followup_hours'])).isoformat()
    c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)', (uid(), tenant, lead['id'], 'Qualify new inquiry', due, 'Pending', 'followup', now()))
    audit(c, tenant, actor, 'lead.created', lead['id'], lead['source'])
    if lead['consent']:
        c.execute('INSERT INTO consent_events VALUES(?,?,?,?,?,?,?)', (uid(), tenant, lead['id'], 1, actor, 'Permission recorded at inquiry intake', now()))
    return lead, True


def match_properties(c, tenant, lead):
    matches = []
    for row in c.execute("SELECT * FROM properties WHERE tenant_id=? AND status='Available'", (tenant,)):
        prop = record(row)
        if prop['intent'] != lead['intent']:
            continue
        if lead['budget'] and prop['price'] > lead['budget']:
            continue
        if lead['bedrooms'] and prop['bedrooms'] < lead['bedrooms']:
            continue
        if lead['min_size'] and prop['size'] < lead['min_size']:
            continue
        if lead['property_type'] and prop['property_type'].casefold() != lead['property_type'].casefold():
            continue
        wanted = [a.casefold() for a in lead.get('amenities', [])]
        if not all(a in [b.casefold() for b in prop['amenities']] for a in wanted):
            continue
        ranking = 40
        reasons = ['Available for ' + prop['intent']]
        if lead['budget']:
            ranking += 20
            reasons.append('Within stated budget')
        if lead['location']:
            if lead['location'].casefold() in prop['location'].casefold():
                ranking += 30
                reasons.append('Matches preferred location')
            else:
                continue
        if lead['bedrooms']:
            ranking += 10
            reasons.append('Meets bedroom requirement')
        matches.append(dict(prop, match_score=ranking, reasons=reasons))
    return sorted(matches, key=lambda p: (-p['match_score'], p['price']))[:6]


def qualify(c, tenant, lead, text):
    lowered = text.casefold().translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
    # Normalize common spoken Egyptian numbers only beside an explicit unit.
    spoken = {'واحد': '1', 'اتنين': '2', 'اثنين': '2', 'تلات': '3', 'ثلاث': '3', 'تلاتة': '3', 'ثلاثة': '3', 'أربع': '4', 'اربعة': '4', 'أربعة': '4', 'خمس': '5', 'خمسة': '5', 'ست': '6', 'ستة': '6', 'سبع': '7', 'سبعة': '7', 'تمان': '8', 'تمانية': '8', 'تسع': '9', 'تسعة': '9', 'عشر': '10', 'عشرة': '10'}
    for word, digit in spoken.items():
        lowered = re.sub(r'(?<!\w)' + word + r'(?=\s+(?:مليون|ألف|غرف))', digit, lowered)
    updates = {}
    budget = re.search(r'(\d+(?:\.\d+)?)\s*(million|m\b|مليون|k\b|thousand|ألف)', lowered)
    if budget:
        multiplier = 1_000_000 if budget[2] in ('million', 'm', 'مليون') else 1000
        updates['budget'] = float(budget[1]) * multiplier
    else:
        budget = re.search(r'(?:budget|ميزاني\S*)\s*[:=]?\s*([\d,]+)', lowered)
        if budget:
            updates['budget'] = float(budget[1].replace(',', ''))
    locations = {'new cairo': 'New Cairo', 'التجمع': 'New Cairo', 'القاهرة الجديدة': 'New Cairo',
                 'sheikh zayed': 'Sheikh Zayed', 'الشيخ زايد': 'Sheikh Zayed', 'dubai': 'Dubai', 'دبي': 'Dubai',
                 'fifth settlement':'Fifth Settlement', 'التجمع الخامس':'Fifth Settlement', 'new capital':'New Capital', 'العاصمة الإدارية':'New Capital', '6th of october':'6th of October', 'السادس من أكتوبر':'6th of October', 'maadi':'Maadi', 'المعادي':'Maadi',
                 'north coast': 'North Coast', 'الساحل': 'North Coast', 'riyadh': 'Riyadh', 'الرياض': 'Riyadh',
                 'abu dhabi': 'Abu Dhabi', 'أبوظبي': 'Abu Dhabi', 'ابوظبي': 'Abu Dhabi', 'jeddah': 'Jeddah', 'جدة': 'Jeddah'}
    for phrase, location in locations.items():
        if phrase in lowered:
            updates['location'] = location
    beds = re.search(r'(\d+)\s*(?:bed|غرف)', lowered)
    if beds:
        bedrooms = int(beds[1])
        if 0 <= bedrooms <= 50:
            updates['bedrooms'] = bedrooms
    if 'budget' in updates and not 0 <= updates['budget'] <= 1e12:
        del updates['budget']
    area = re.search(r'(\d+(?:\.\d+)?)\s*(?:m²|m2|sqm|متر(?:\s*مربع)?)', lowered)
    if area and 0 < float(area[1]) <= 1_000_000:
        updates['min_size'] = float(area[1])
    amenities = {'pool': 'Pool', 'حمام سباحة': 'Pool', 'gym': 'Gym', 'جيم': 'Gym', 'parking': 'Parking', 'جراج': 'Parking', 'garden': 'Garden', 'حديقة': 'Garden', 'security': 'Security', 'أمن': 'Security', 'beach': 'Beach', 'شاطئ': 'Beach'}
    requested = [value for phrase, value in amenities.items() if phrase in lowered]
    if requested:
        updates['amenities'] = list(dict.fromkeys([*lead.get('amenities', []), *requested]))
    if any(word in lowered for word in ('rent', 'إيجار', 'ايجار')):
        updates['intent'] = 'rent'
    elif any(word in lowered for word in ('buy', 'شراء', 'اشتري')):
        updates['intent'] = 'buy'
    for words, kind in [(('apartment', 'شقة', 'شقه'), 'Apartment'), (('villa', 'فيلا'), 'Villa'), (('office', 'مكتب'), 'Office'), (('duplex', 'دوبلكس'), 'Duplex'), (('penthouse', 'بنتهاوس'), 'Penthouse'), (('commercial', 'محل', 'تجاري'), 'Commercial')]:
        if any(word in lowered for word in words):
            updates['property_type'] = kind
    if any(word in lowered for word in ('stop', 'unsubscribe', 'إلغاء', 'متبعتش', 'وقف الرسائل')):
        updates['opted_out'] = True
        updates['consent'] = False
    elif any(word in lowered for word in ('i agree to follow-up', 'i consent to follow-up', 'موافق على المتابعة', 'موافق على رسائل المتابعة')):
        updates['opted_out'] = False
        updates['consent'] = True
    if 'consent' in updates:
        c.execute('INSERT INTO consent_events VALUES(?,?,?,?,?,?,?)', (uid(), tenant, lead['id'], int(updates['consent']), 'customer', 'Explicit opt-in phrase' if updates['consent'] else 'Opt-out phrase', now()))
        if not updates['consent']:
            c.execute("UPDATE outbox SET status='Held',error='Customer opted out' WHERE tenant_id=? AND lead_id=? AND status IN ('Pending','Retry')", (tenant, lead['id']))
    if updates:
        lead.update(updates)
        updates['score'] = score(lead)
        if lead['budget'] and lead['location'] and lead['stage'] == 'New':
            updates['stage'] = 'Qualified'
        updates['updated_at'] = now()
        stored = dict(updates)
        if 'amenities' in stored:
            stored['amenities'] = json.dumps(stored['amenities'])
        c.execute(f"UPDATE leads SET {','.join(k+'=?' for k in stored)} WHERE tenant_id=? AND id=?", [*stored.values(), tenant, lead['id']])
        lead.update(updates)
    return lead


def human_requested(text):
    return any(w in text.casefold() for w in ('human', 'complaint', 'إنسان', 'موظف', 'شكوى', 'legal', 'عقد', 'مستشار', 'حد يكلمني'))


def rules_reply(c, tenant, lead, text, language=None):
    arabic = language == 'ar' if language else bool(re.search('[\u0600-\u06ff]', text))
    if lead['opted_out']:
        return ('تمام، وقفنا رسائل المتابعة. مش هنبعت لك تاني إلا بموافقتك.' if arabic else 'Follow-up messages are stopped.'), []
    if human_requested(text):
        from .operations import set_handoff
        set_handoff(c, tenant, lead['id'], True, 'Customer requested an adviser', 'assistant')
        return ('أكيد، سجّلنا طلبك ومستشار عقاري هيتابع معاك. الردود الآلية متوقفة لحد ما المستشار يرجع المساعد.' if arabic else 'I have recorded your request for a human adviser.'), []
    matches = match_properties(c, tenant, lead)
    currency = settings(c, tenant)['currency']
    missing = []
    if not lead['budget']:
        missing.append('الميزانية' if arabic else 'budget')
    if not lead['location']:
        missing.append('المنطقة المفضلة' if arabic else 'preferred location')
    if missing:
        return (('أهلاً بيك. ممكن أعرف ' + ' و'.join(missing) + ' عشان نرشّح لك المناسب؟') if arabic else 'What is your ' + ' and '.join(missing) + '?'), matches
    if not matches:
        return ('حالياً مفيش عقارات متاحة مطابقة لطلبك. تحب نعدّل المنطقة أو الميزانية، ولا مستشار يساعدك؟' if arabic else 'No available properties match these requirements. Would you like to adjust the search?'), []
    lines = [f"{p['title']} — {p['price']:,.0f} {currency}, {p['bedrooms']} {'غرف' if arabic else 'bedrooms'}, {p['size']:g} m²" for p in matches[:3]]
    prefix = 'دي العقارات المتاحة اللي بتطابق طلبك:' if arabic else 'These available properties match your requirements:'
    suffix = 'اختار العقار المناسب وموعد معاينة متاح من التقويم. الحجز بيتأكد بعد اختيار الموعد.' if arabic else 'Choose a property and an available viewing time in the booking calendar.'
    if any(p.get('sample') for p in matches[:3]):
        suffix = ('العقارات المعلّمة تجريبية / خيالية، وليست عروض بيع حقيقية. ' if arabic else 'Listings marked Sample / Fictional are demonstration inventory, not real offers. ') + suffix
        lines = [line + (' · تجريبي / خيالي' if arabic else ' · Sample / Fictional') if p.get('sample') else line for line,p in zip(lines,matches)]
    return prefix + '\n' + '\n'.join(lines) + '\n' + suffix, matches


def book(c, tenant, data, actor):
    lead = require(c, 'leads', tenant, data['lead_id'])
    prop = require(c, 'properties', tenant, data['property_id'])
    agent = require(c, 'users', tenant, data['agent_id'])
    if agent.get('sample') or not agent['active'] or prop['status'] != 'Available':
        raise HTTPException(409, 'Agent or property unavailable')
    try:
        start = datetime.fromisoformat(data['start_at'].replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(422, 'Use a valid ISO appointment time')
    if start.tzinfo is None:
        raise HTTPException(422, 'Appointment time needs a timezone')
    start = start.astimezone(timezone.utc)
    end = start + timedelta(minutes=60)
    cfg = settings(c, tenant)
    local_start = start.astimezone(ZoneInfo(cfg['timezone']))
    local_end = end.astimezone(ZoneInfo(cfg['timezone']))
    if start < datetime.now(timezone.utc) or not (cfg['business_start'] <= local_start.hour and local_end.hour <= cfg['business_end'] and local_start.date() == local_end.date()):
        raise HTTPException(422, 'Choose a future time within company business hours')
    a, b = start.isoformat(), end.isoformat()
    # Caller holds BEGIN IMMEDIATE, preventing concurrent check/insert races.
    conflict = c.execute("SELECT id FROM appointments WHERE tenant_id=? AND status='Booked' AND (agent_id=? OR lead_id=? OR property_id=?) AND start_at<? AND end_at>? AND id<>?", (tenant, data['agent_id'], lead['id'], prop['id'], b, a, data.get('id', ''))).fetchone()
    if conflict:
        raise HTTPException(409, 'This time overlaps an existing appointment')
    data = dict(data)
    if prop.get('sample'):
        label = 'Sample / Fictional viewing; fictional customer. ' if lead.get('sample') else 'Demonstration viewing of a Sample / Fictional property; customer interaction is genuine. '
        if not data.get('notes', '').startswith(label):
            data['notes'] = label + data.get('notes', '')
    appointment_id = data.get('id') or uid()
    if data.get('id'):
        require(c, 'appointments', tenant, appointment_id)
        c.execute("UPDATE appointments SET start_at=?,end_at=?,status='Booked',agent_id=?,property_id=?,notes=? WHERE tenant_id=? AND id=?", (a, b, agent['id'], prop['id'], data.get('notes', ''), tenant, appointment_id))
    else:
        c.execute('INSERT INTO appointments VALUES(?,?,?,?,?,?,?,?,?,?)', (appointment_id, tenant, lead['id'], prop['id'], agent['id'], a, b, 'Booked', data.get('notes', ''), now()))
    c.execute("UPDATE leads SET stage='Viewing',updated_at=? WHERE tenant_id=? AND id=?", (now(), tenant, lead['id']))
    audit(c, tenant, actor, 'appointment.booked', appointment_id, a)
    audit(c, tenant, actor, 'lead.viewing_confirmed', lead['id'], appointment_id + ' · ' + prop['title'] + ' · ' + a)
    return require(c, 'appointments', tenant, appointment_id)


def insights(c, tenant):
    leads = [record(r) for r in c.execute('SELECT * FROM leads WHERE tenant_id=?', (tenant,))]
    current = datetime.now(timezone.utc)
    result = []
    for lead in leads:
        if lead.get('sample'):
            continue
        if lead['stage'] in ('Won', 'Lost'):
            continue
        age = (current - datetime.fromisoformat(lead['updated_at'])).total_seconds() / 3600
        if age > 24 and lead['stage'] == 'Negotiation':
            result.append({'lead_id': lead['id'], 'name': lead['name'], 'type': 'Deal risk', 'priority': 'High', 'action': 'Confirm decision timeline: negotiation has stalled', 'evidence': f'{age:.0f} hours without CRM activity in negotiation'})
        if age > 48:
            result.append({'lead_id': lead['id'], 'name': lead['name'], 'type': 'Leakage', 'priority': 'High', 'action': 'Contact lead: no CRM activity for more than 48 hours', 'evidence': f'{age:.0f} hours without activity'})
        elif lead['budget'] and not match_properties(c, tenant, lead):
            result.append({'lead_id': lead['id'], 'name': lead['name'], 'type': 'Inventory gap', 'priority': 'Medium', 'action': 'Review preferences or source matching inventory', 'evidence': 'No available inventory matches recorded requirements'})
        else:
            action = 'Book a viewing' if lead['score'] >= 65 else 'Confirm budget and preferred area'
            result.append({'lead_id': lead['id'], 'name': lead['name'], 'type': 'Next best action', 'priority': 'High' if lead['score'] >= 65 else 'Normal', 'action': action, 'evidence': f"Recorded qualification score {lead['score']}/100"})
    return result


def channel_followup(c, tenant, row, body):
    if row['source'] != 'telegram':
        return body
    language = c.execute('SELECT language FROM telegram_contacts WHERE tenant_id=? AND lead_id=?', (tenant, row['lead_id'])).fetchone()
    if body.startswith('Viewing reminder: '):
        from .telegram_messages import appointment_date, timezone_label, text as safe_text
        stamp = body.removeprefix('Viewing reminder: ')
        arabic = bool(language and language[0] == 'ar')
        zone = settings(c, tenant).get('timezone')
        return ('📅 تذكير بموعد المعاينة: ' if arabic else '📅 Viewing reminder: ') + appointment_date(stamp, arabic, zone, include_year=True) + '\n' + ('🕒 التوقيت: ' if arabic else '🕒 Timezone: ') + safe_text(timezone_label(stamp, zone), arabic)
    if language and language[0] == 'ar':
        if body.startswith('Viewing reminder: '):
            body = 'تذكير بموعد المعاينة: ' + body.removeprefix('Viewing reminder: ')
        elif body.startswith('Available properties matching your recorded preferences: '):
            body = 'عقارات متاحة تناسب تفضيلاتك: ' + body.removeprefix('Available properties matching your recorded preferences: ')
        else:
            body = 'مستشارك العقاري جاهز لمتابعة طلبك. استخدم /properties للعقارات أو /agent للتواصل مع المستشار.'
    return body


def tick(c, tenant):
    count = 0
    due = now()
    for row in c.execute("SELECT t.*,l.source,l.consent,l.opted_out FROM tasks t JOIN leads l ON l.id=t.lead_id AND l.tenant_id=t.tenant_id WHERE t.tenant_id=? AND t.status='Pending' AND t.kind<>'handoff' AND t.due_at<=? AND NOT EXISTS (SELECT 1 FROM conversation_controls cc WHERE cc.lead_id=l.id AND cc.tenant_id=l.tenant_id AND cc.human_active=1)", (tenant, due)).fetchall():
        if row['lead_id'].startswith('sample-') or not row['consent'] or row['opted_out']:
            continue
        body = 'Your property adviser is ready to help with your inquiry.'
        if row['kind'] == 'availability':
            lead = require(c, 'leads', tenant, row['lead_id'])
            matches = match_properties(c, tenant, lead)
            if not matches:
                continue
            body = 'Available properties matching your recorded preferences: ' + ', '.join(p['title'] for p in matches[:3])
        cursor = c.execute('INSERT OR IGNORE INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (uid(), tenant, row['lead_id'], row['source'], channel_followup(c, tenant, row, body), '', 'task:' + row['id'], 'Pending', 0, due, '', '', due))
        count += cursor.rowcount
    horizon = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    for row in c.execute("SELECT a.*,l.source,l.consent,l.opted_out FROM appointments a JOIN leads l ON l.id=a.lead_id AND l.tenant_id=a.tenant_id WHERE a.tenant_id=? AND a.status='Booked' AND a.start_at>? AND a.start_at<=?", (tenant, due, horizon)).fetchall():
        if row['lead_id'].startswith('sample-') or not row['consent'] or row['opted_out']:
            continue
        cursor = c.execute('INSERT OR IGNORE INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (uid(), tenant, row['lead_id'], row['source'], channel_followup(c, tenant, row, 'Viewing reminder: ' + row['start_at']), '', 'appointment:' + row['id'] + ':' + row['start_at'], 'Pending', 0, due, '', '', due))
        count += cursor.rowcount
    # Once-per-lead reactivation and retention; consent and opt-out are enforced.
    dormant = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    for row in c.execute("SELECT * FROM leads l WHERE tenant_id=? AND consent=1 AND opted_out=0 AND NOT EXISTS (SELECT 1 FROM conversation_controls cc WHERE cc.lead_id=l.id AND cc.tenant_id=l.tenant_id AND cc.human_active=1) AND ((updated_at<? AND stage NOT IN ('Won','Lost')) OR stage='Won')", (tenant, dormant)).fetchall():
        if row['id'].startswith('sample-'):
            continue
        kind = 'retention' if row['stage'] == 'Won' else 'reactivation'
        text = 'Your property adviser is available if you need further help.' if kind == 'retention' else 'Would you like to review your property search preferences?'
        cursor = c.execute('INSERT OR IGNORE INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (uid(), tenant, row['id'], row['source'], channel_followup(c, tenant, dict(row, lead_id=row['id']), text), '', kind + ':' + row['id'], 'Pending', 0, due, '', '', due))
        count += cursor.rowcount
    audit(c, tenant, 'automation', 'automation.tick', tenant, f'{count} messages queued; delivery requires approval')
    return {'queued': count}
