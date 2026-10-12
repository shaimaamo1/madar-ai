"""Customer-facing Telegram plain text. No parse_mode, locale service or paid API."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

AR_DAYS = ('الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد')
EN_DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
AR_MONTHS = ('يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر')
EN_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')


def text(value, arabic=False):
    """Single-line inventory text, with safe direction isolation in Arabic messages.

    Telegram receives plain text (no HTML/Markdown parse_mode), so dynamic angle
    brackets/asterisks are literal, not markup. Remove injected control characters
    and newlines to keep inventory values from impersonating other message fields.
    """
    value = re.sub(r'[\x00-\x1f\x7f\u200e\u200f\u202a-\u202e\u2066-\u2069]', ' ', str(value))
    value = ' '.join(value.split())[:180]
    return '\u2068' + value + '\u2069' if arabic else value


def workspace_zone(name=None):
    try:
        return ZoneInfo(name or 'Africa/Cairo')
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return ZoneInfo('Africa/Cairo')


def local_time(stamp, zone=None):
    instant = datetime.fromisoformat(stamp.replace('Z', '+00:00')) if isinstance(stamp, str) else stamp
    if instant.tzinfo is None:
        # Legacy naive stored values are interpreted as UTC, never host-local time.
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(workspace_zone(zone))


def appointment_date(stamp, arabic, zone=None, include_year=False):
    local = local_time(stamp, zone)
    hour = local.hour % 12 or 12
    clock = f'{hour}:{local.minute:02}'
    if arabic:
        date = f'{AR_DAYS[local.weekday()]} {local.day} {AR_MONTHS[local.month-1]}'
        if include_year:
            date += f' {local.year}'
        return date + ' – ' + clock + (' صباحًا' if local.hour < 12 else ' مساءً')
    date = f'{EN_DAYS[local.weekday()]}, {EN_MONTHS[local.month-1]} {local.day}'
    if include_year:
        date += f', {local.year}'
    return date + ' – ' + clock + (' AM' if local.hour < 12 else ' PM')


def timezone_label(stamp, zone=None):
    local = local_time(stamp, zone)
    offset = local.strftime('%z')
    return f'{local.tzinfo.key} (UTC{offset[:3]}:{offset[3:]})'


def property_recommendations(properties, currency, arabic):
    blocks=[]
    for prop in properties[:3]:
        price = format(prop['price'], ',.0f' if float(prop['price']).is_integer() else ',.2f')
        lines = ['🏠 ' + text(prop['title'], arabic),
                 ('📍 الموقع: ' if arabic else '📍 Location: ') + text(prop['location'], arabic),
                 ('💰 السعر: ' if arabic else '💰 Price: ') + text(price + ' ' + currency, arabic) +
                 ((' شهريًا' if arabic else ' / month') if prop['intent']=='rent' else ''),
                 ('📐 المساحة: ' if arabic else '📐 Area: ') + text(f"{prop['size']:g} m²", arabic)]
        if prop['bedrooms'] > 0:
            lines.append(('🛏 غرف النوم: ' if arabic else '🛏 Bedrooms: ') + text(prop['bedrooms'], arabic))
        blocks.append('\n'.join(lines))
    intro = 'إليك العقارات المتاحة التي تناسب طلبك:' if arabic else 'These available properties match your requirements:'
    action = 'اختر زر المعاينة أسفل الرسالة للاطلاع على المواعيد المتاحة.' if arabic else 'Choose a viewing button below to see available times.'
    return intro + '\n\n' + '\n\n'.join(blocks) + '\n\n' + action


def booking_message(prop, stamp, arabic, zone, reference=None):
    confirmed = reference is not None
    heading = ('✅ تم تأكيد المعاينة' if arabic else '✅ Your viewing is confirmed') if confirmed else ('هل ترغب في تأكيد هذه المعاينة؟' if arabic else 'Would you like to confirm this viewing?')
    lines = [heading, '', '🏠 ' + text(prop['title'], arabic),
             ('📅 الموعد: ' if arabic else '📅 Date and time: ') + appointment_date(stamp, arabic, zone, include_year=True),
             ('🕒 التوقيت: ' if arabic else '🕒 Timezone: ') + text(timezone_label(stamp, zone), arabic)]
    if confirmed:
        lines += [('🔖 رقم الحجز: ' if arabic else '🔖 Booking reference: ') + text(reference, arabic), '',
                  'لأي استفسار، استخدم زر التواصل مع مستشار أدناه.' if arabic else 'For assistance, use the contact-an-agent button below.']
    else:
        lines += ['', 'لم يتم الحجز بعد. اضغط «تأكيد الحجز» لإتمامه.' if arabic else 'Not booked yet. Select Confirm booking to finalize your viewing.']
    return '\n'.join(lines)
