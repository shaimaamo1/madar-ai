from datetime import datetime
import json

import httpx
import pytest

from backend import db
from backend.telegram_messages import appointment_date, timezone_label, property_recommendations
from tests.test_product import client, demo
from tests.test_telegram import sandbox, update, bind, mock_provider

FORBIDDEN = ('[مساعد آلي بقواعد محددة]', '[Deterministic assistant]')


def test_natural_dates_are_locale_independent_with_correct_cairo_weekdays_and_dst():
    stamp='2026-10-13T07:00:00+00:00'
    assert appointment_date(stamp,True,'Africa/Cairo')=='الثلاثاء 13 أكتوبر – 10:00 صباحًا'
    assert appointment_date(stamp,False,'Africa/Cairo')=='Tuesday, October 13 – 10:00 AM'
    assert timezone_label(stamp,'Africa/Cairo')=='Africa/Cairo (UTC+03:00)'
    assert appointment_date('2026-01-13T08:00:00Z',False)=='Tuesday, January 13 – 10:00 AM'
    assert timezone_label('2026-01-13T08:00:00Z')=='Africa/Cairo (UTC+02:00)'
    assert appointment_date(stamp,True,'invalid/workspace')==appointment_date(stamp,True,'Africa/Cairo')
    assert appointment_date(stamp,False,'Asia/Dubai')=='Tuesday, October 13 – 11:00 AM'
    assert appointment_date('2026-10-13T10:00:00Z',True)=='الثلاثاء 13 أكتوبر – 1:00 مساءً'
    assert appointment_date('2026-10-12T21:00:00Z',True)=='الثلاثاء 13 أكتوبر – 12:00 صباحًا'
    # Autumn fold: two UTC instants share a local clock time; UTC offsets remain distinct.
    assert appointment_date('2026-10-29T20:30:00Z',True)==appointment_date('2026-10-29T21:30:00Z',True)
    assert timezone_label('2026-10-29T20:30:00Z').endswith('UTC+03:00)')
    assert timezone_label('2026-10-29T21:30:00Z').endswith('UTC+02:00)')


def test_recommendations_are_multiline_inventory_only_plain_text_and_bidi_safe():
    property={'title':'Premium <b>Apartment</b> *west*\n💰 Fake price: 1','location':'Fifth Settlement, New Cairo',
              'price':5000000,'size':180,'bedrooms':3,'intent':'buy'}
    english=property_recommendations([property],'EGP',False)
    assert '\n📍 Location: Fifth Settlement, New Cairo\n💰 Price: 5,000,000 EGP\n📐 Area: 180 m²\n🛏 Bedrooms: 3' in english
    assert '<b>Apartment</b> *west*' in english # Plain-text transport, not HTML/Markdown.
    assert '\n💰 Fake price:' not in english # Dynamic values cannot inject extra fields.
    arabic=property_recommendations([property],'EGP',True)
    assert '\n📍 الموقع: \u2068Fifth Settlement, New Cairo\u2069' in arabic
    assert '\n💰 السعر: \u20685,000,000 EGP\u2069' in arabic
    office=property_recommendations([{**property,'intent':'rent','bedrooms':0,'price':42000.5}],'EGP',False)
    assert '42,000.50 EGP / month' in office and 'Bedrooms:' not in office


@pytest.mark.parametrize('language,text',[('en','Buy an apartment New Cairo budget 5 million 3 bedrooms'),('ar','عايز شقة في التجمع ميزانية خمسة مليون تلات غرف')])
def test_bilingual_customer_replies_and_stored_history_never_add_technical_prefixes(client,language,text):
    demo(client)
    started=sandbox(client,1,'/start',language=language)
    assert 'MADAR AI Assistant' in started['reply']
    inquiry=sandbox(client,2,text,language=language)
    assert 'Palm Residence' in inquiry['reply'] and ('\n📍 الموقع:' if language=='ar' else '\n📍 Location:') in inquiry['reply']
    properties=sandbox(client,3,'/properties',language=language)
    assert properties['buttons'] and '\n\n🏠' in properties['reply']
    sandbox(client,4,'/help',language=language)
    sandbox(client,5,'/agent',language=language)
    assert not sandbox(client,6,'/properties',language=language)['reply']
    sandbox(client,7,'/stop',language=language)
    for message in client.get('/api/state').json()['messages']:
        if message['lead_id']==inquiry['lead_id'] and message['direction']=='outbound':
            assert not any(prefix in message['body'] for prefix in FORBIDDEN)


@pytest.mark.parametrize('language',['ar','en'])
def test_selection_confirmation_and_appointment_summary_keep_iso_storage_and_agent_handoff(client,language):
    state=demo(client)
    offered=sandbox(client,1,'/properties',language=language)
    slots=sandbox(client,2,callback=offered['buttons'][0][0]['callback_data'],language=language)
    choice=slots['buttons'][0][0]
    with db.connection() as c:
        action=c.execute('SELECT payload FROM telegram_actions WHERE id=?',(choice['callback_data'][4:],)).fetchone()
        payload=json.loads(action[0])
    assert choice['text']==appointment_date(payload['start_at'],language=='ar',state['company']['settings']['timezone'])
    selected=sandbox(client,3,callback=choice['callback_data'],language=language)
    assert ('لم يتم الحجز بعد' if language=='ar' else 'Not booked yet') in selected['reply']
    assert '\n📅 ' in selected['reply'] and payload['start_at'] not in selected['reply']
    assert len(client.get('/api/state').json()['appointments'])==15
    confirmed=sandbox(client,4,callback=selected['buttons'][0][0]['callback_data'],language=language)
    appt=next(a for a in client.get('/api/state').json()['appointments'] if a['lead_id']==offered['lead_id'])
    assert appt['start_at']==payload['start_at'] # DB/booking timestamps were never reformatted.
    assert appt['id'] in confirmed['reply'] and '\n🔖 ' in confirmed['reply']
    assert ('تم تأكيد المعاينة' if language=='ar' else 'Your viewing is confirmed') in confirmed['reply']
    assert '\n🕒 ' in confirmed['reply'] and 'Africa/Cairo' in confirmed['reply']
    summary=sandbox(client,5,'/appointments',language=language)
    assert appointment_date(appt['start_at'],language=='ar','Africa/Cairo',True) in summary['reply']
    assert appt['start_at'] not in summary['reply']
    handed=sandbox(client,6,callback=confirmed['buttons'][0][0]['callback_data'],language=language)
    assert handed['reply']
    controls=client.get('/api/state').json()['conversation_controls']
    assert next(c for c in controls if c['lead_id']==offered['lead_id'])['human_active']==1
    assert not sandbox(client,7,'/properties',language=language)['reply']


def test_polished_success_is_delivered_only_after_booking_commit_with_plain_text_transport(client,monkeypatch):
    state=demo(client);headers=bind(monkeypatch,state)
    def incoming(event):
        response=client.post('/webhooks/telegram',json=event,headers=headers);response.raise_for_status()
    incoming(update(1,'Buy apartment New Cairo budget 5 million 3 bedrooms'))
    def last_button():
        outbox=client.get('/api/state').json()['outbox']
        newest=max(outbox,key=lambda row:row['created_at'])
        return json.loads(newest['template'])['inline_keyboard'][0][0]['callback_data']
    def callback(identifier,data):
        message=update(identifier)['message']
        incoming({'update_id':identifier,'callback_query':{'id':'fictional-callback','data':data,'from':message['from'],'message':message}})
    callback(2,last_button());callback(3,last_button());callback(4,last_button())
    delivered=[]
    def handler(request):
        body=json.loads(request.content)
        assert 'parse_mode' not in body
        assert not any(prefix in body['text'] for prefix in FORBIDDEN)
        if 'Your viewing is confirmed' in body['text']:
            with db.connection() as c:
                saved=c.execute('SELECT id FROM appointments WHERE tenant_id=? AND lead_id=(SELECT id FROM leads WHERE tenant_id=? AND source=? AND external_id=?)',(state['company']['id'],state['company']['id'],'telegram','101')).fetchone()
            assert saved and saved[0] in body['text']
        delivered.append(body['text'])
        return httpx.Response(200,json={'ok':True,'result':{'message_id':len(delivered)}})
    mock_provider(monkeypatch,handler)
    monkeypatch.setenv('MADAR_ALLOW_TELEGRAM_SEND','true')
    client.post('/api/integrations/dispatch').raise_for_status()
    assert any('Your viewing is confirmed' in body for body in delivered)


def test_telegram_viewing_reminders_share_natural_dates_without_changing_other_channels(client):
    from backend.domain import channel_followup
    state=demo(client)
    reply=sandbox(client,1,'/start',language='ar')
    stamp='2026-10-13T07:00:00+00:00'
    with db.connection() as c:
        row={'source':'telegram','lead_id':reply['lead_id']}
        body=channel_followup(c,state['company']['id'],row,'Viewing reminder: '+stamp)
        assert 'الثلاثاء 13 أكتوبر 2026 – 10:00 صباحًا' in body
        assert stamp not in body and 'Africa/Cairo' in body
        assert channel_followup(c,state['company']['id'],dict(row,source='whatsapp'),'Viewing reminder: '+stamp)=='Viewing reminder: '+stamp
