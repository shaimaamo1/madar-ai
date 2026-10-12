"""Idempotent, isolated demonstration records. Never invokes providers or automation."""
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .db import now, settings
from .domain import score
from .demo_inventory import LISTINGS, NAMES, AGENTS

TABLES = ('messages','tasks','deals','appointments','conversation_controls','activities','consent_events','leads','properties','users')


def require_demo(c, tenant):
    row = c.execute('SELECT demo FROM tenants WHERE id=?', (tenant,)).fetchone()
    if not row or not row[0]:
        raise HTTPException(403, 'Demo data is available only in isolated fictional workspaces')


def identity(tenant, kind, index):
    return f'demo-{kind}-{tenant}-{index:03}'


def insert(c, tenant, table, record):
    existing = c.execute(f'SELECT 1 FROM {table} WHERE id=? AND tenant_id=?', (record['id'], tenant)).fetchone()
    if existing:
        return
    c.execute(f"INSERT INTO {table} ({','.join(record)}) VALUES ({','.join('?' for _ in record)})", list(record.values()))
    c.execute('INSERT OR IGNORE INTO demo_seed_records VALUES(?,?,?)', (tenant, table, record['id']))


def seed_demo(c, tenant, admin, password_hash):
    require_demo(c, tenant)
    anchor = c.execute('SELECT anchor_at FROM demo_datasets WHERE tenant_id=?', (tenant,)).fetchone()
    stamp = anchor[0] if anchor else now()
    c.execute('INSERT OR IGNORE INTO demo_datasets VALUES(?,?,?)', (tenant, 'egypt-portfolio-v1', stamp))
    clock = datetime.fromisoformat(stamp)
    zone = ZoneInfo(settings(c, tenant)['timezone'])
    agents=[]
    for i,name in enumerate(AGENTS):
        identifier=identity(tenant,'agent',i+1);agents.append(identifier)
        insert(c,tenant,'users',dict(id=identifier,tenant_id=tenant,email=f'agent{i+1}@demo.invalid',name=name,role='agent',password_hash=password_hash,active=1))
    props=[]
    for i,(title,location,kind,intent,price,area,beds,amenities) in enumerate(LISTINGS):
        identifier=identity(tenant,'property',i+1);props.append(identifier)
        status={7:'Reserved',11:'Reserved',19:'Sold',22:'Sold',24:'Rented',26:'Reserved'}.get(i,'Available')
        description=f'DEMO / FICTIONAL — {title}. An illustrative {area:g} m² {kind.lower()} in {location}, '+('with '+str(beds)+' bedrooms and ' if beds else 'with ')+', '.join(amenities).lower()+'. Photorealistic synthetic illustrative image; not a verified photograph, listing or market valuation.'
        insert(c,tenant,'properties',dict(id=identifier,tenant_id=tenant,title=title,location=location,property_type=kind,intent=intent,price=price,size=area,bedrooms=beds,amenities=json.dumps(amenities),status=status,description=description,image=f'/demo-assets/property-{i+1:02}.webp',created_at=(clock-timedelta(days=30-i)).isoformat()))
    leads=[];targets=[]
    sources=['website','whatsapp','facebook','telegram','website','email','instagram','crm']
    stages=['Qualified','Viewing','New','Negotiation','Won','Lost']
    for i,name in enumerate(NAMES):
        target=[0,2,1,4,0,1][i] if i<6 else i%30
        prop=LISTINGS[target];targets.append(target)
        identifier=identity(tenant,'customer',i+1);leads.append(identifier)
        budget=2800000 if i==5 else round(prop[4]*1.1,-3)
        location='Aswan' if i==5 else prop[1]
        data=dict(id=identifier,tenant_id=tenant,name=name,phone='',email=f'customer{i+1:02}@demo.invalid',source=sources[i%len(sources)],external_id=f'sandbox:demo-customer-{i+1:02}',stage=('Viewing' if i in (6,8,9,10,12,13,14,15) else 'Qualified' if i==2 else stages[i%6]),budget=budget,location=location,property_type=prop[2],intent=prop[3],bedrooms=prop[6],min_size=max(prop[5]-25,0),amenities=json.dumps([]),score=0,assigned_to=agents[i%5],consent=int(i%4!=0),opted_out=int(i in (5,29)),created_at=(clock-timedelta(days=24-i%20)).isoformat(),updated_at=(clock-timedelta(hours=i%7*10)).isoformat())
        if data['opted_out']:data['consent']=0
        data['score']=score(data)
        insert(c,tenant,'leads',data)
        insert(c,tenant,'activities',dict(id=identity(tenant,'activity',i+1),tenant_id=tenant,actor=agents[i%5],action='lead.demo_seeded',entity_id=identifier,detail='DEMO / FICTIONAL — '+data['stage']+' inquiry from '+data['source'],created_at=data['updated_at']))
    # Fifteen appointments share real demo lead/property/adviser IDs, with no overlaps.
    appointments={}
    for i in range(15):
        lead_index=[0,1,2,3,4,6,8,9,10,12,13,14,15,16,18][i]
        start=(clock.astimezone(zone)+timedelta(days=(-8+i if i<5 else 1+i//5))).replace(hour=10+i%5,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
        state='Completed' if i<5 else 'Cancelled' if i in (13,14) else 'Booked'
        prop_index=targets[lead_index]
        if state=='Booked' and prop_index in (7,11,19,22,24,26):
            state='Cancelled'
        identifier=identity(tenant,'appointment',i+1)
        appointments[lead_index]=(identifier,state,start.isoformat(),prop_index)
        insert(c,tenant,'appointments',dict(id=identifier,tenant_id=tenant,lead_id=leads[lead_index],property_id=props[prop_index],agent_id=agents[lead_index%5],start_at=start.isoformat(),end_at=(start+timedelta(hours=1)).isoformat(),status=state,notes='DEMO / FICTIONAL — illustrative viewing; never published to an external calendar.',created_at=(clock-timedelta(days=10)).isoformat()))
    for i in range(20):
        completed=i%4==0
        insert(c,tenant,'tasks',dict(id=identity(tenant,'task',i+1),tenant_id=tenant,lead_id=leads[i],title=['Confirm budget and area','Collect post-viewing feedback','Review matching inventory','Arrange adviser callback'][i%4],due_at=(clock+timedelta(hours=i*3-12)).isoformat(),status='Completed' if completed else 'Pending',kind='followup',created_at=(clock-timedelta(days=2)).isoformat()))
    # Twenty-five four-message conversations; references stay grounded in seeded inventory/bookings.
    for i in range(25):
        prop=LISTINGS[targets[i]];arabic=i%2==0
        arabic_type={'Apartment':'شقة','Villa':'فيلا','Duplex':'دوبلكس','Penthouse':'بنتهاوس','Office':'مكتب','Commercial':'محل تجاري'}[prop[2]]
        arabic_location={'New Cairo':'القاهرة الجديدة','Fifth Settlement':'التجمع الخامس','New Capital':'العاصمة الإدارية','Sheikh Zayed':'الشيخ زايد','6th of October':'السادس من أكتوبر','Maadi':'المعادي','North Coast':'الساحل الشمالي'}[prop[1]]
        inbound=(f'أبحث عن {arabic_type} في {arabic_location}، ميزانيتي {int(LISTINGS[targets[i]][4]*1.1):,} جنيه. هل يوجد عقار مناسب؟' if arabic else f'I am looking for a {prop[2].lower()} in {prop[1]}, budget EGP {int(prop[4]*1.1):,}. Is anything available?')
        if i==5:
            inbound='I need an apartment in Aswan with a budget of EGP 2,800,000.'
            answer='There is no available inventory matching Aswan. May an adviser help review alternative areas?'
        elif i in (7,11,19,22,24):
            answer=('العقار المختار غير متاح حالياً. يمكن للمستشار اقتراح بدائل من المخزون المتاح.' if arabic else 'The selected listing is unavailable. An adviser can help review available alternatives.')
        else:
            answer=(f'لدينا {prop[0]}، {prop[5]:g} متر مربع، بسعر توضيحي {prop[4]:,} جنيه '+('شهرياً.' if prop[3]=='rent' else '.') if arabic else f'{prop[0]} offers {prop[5]:g} m² at an illustrative EGP {prop[4]:,}'+('/month.' if prop[3]=='rent' else '.'))
        if i in (17,23):
            follow='أريد التحدث مع مستشار بشري.' if arabic else 'Could a human adviser call me about the requirements?'
            reply='تم تحويل المحادثة لمستشارك، والردود الآلية متوقفة حتى يعود المساعد.' if arabic else 'Your adviser is taking over. Automated replies are paused until the adviser releases the conversation.'
            if not c.execute('SELECT 1 FROM conversation_controls WHERE lead_id=?',(leads[i],)).fetchone():
                c.execute('INSERT INTO conversation_controls VALUES(?,?,?,?,?)',(leads[i],tenant,1,'DEMO adviser handoff',stamp))
                c.execute('INSERT OR IGNORE INTO demo_seed_records VALUES(?,?,?)',(tenant,'conversation_controls',leads[i]))
        elif i in appointments and appointments[i][1] in ('Booked','Completed'):
            follow='هل تم تأكيد موعد المعاينة؟' if arabic else 'Can you confirm the viewing details?'
            booking=appointments[i]
            formatted=datetime.fromisoformat(booking[2]).astimezone(zone).strftime('%Y-%m-%d %H:%M')
            reply=(f'المعاينة المسجلة للعقار {prop[0]} في {formatted} ({zone.key}). هذه محاكاة في مساحة العرض.' if arabic else f'Recorded demo viewing: {prop[0]}, {formatted} ({zone.key}). This is an isolated demonstration booking.')
        else:
            follow='شكراً، أحتاج إلى مراجعة الميزانية قبل اختيار موعد.' if arabic else 'Thank you. I need to review the budget before choosing a viewing.'
            reply='بالطبع. يمكننا متابعة البحث بعد موافقتك على رسائل المتابعة.' if arabic else 'Of course. We can continue the search with your permission for follow-up messages.'
        for sequence,(direction,body) in enumerate([('inbound',inbound),('outbound',answer),('inbound',follow),('outbound',reply)]):
            insert(c,tenant,'messages',dict(id=identity(tenant,'message',i*4+sequence+1),tenant_id=tenant,lead_id=leads[i],direction=direction,channel=sources[i%len(sources)],body=body,external_id=f'sandbox:demo-conversation-{i+1:02}-{sequence}' if direction=='inbound' else '',created_at=(clock-timedelta(days=i%7,hours=2)+timedelta(minutes=sequence*3)).isoformat()))
    return props


def reset_generated(c, tenant):
    """Delete only tracked seed rows; preserve parents referenced by added records."""
    require_demo(c,tenant)
    owned={table:{r[0] for r in c.execute('SELECT record_id FROM demo_seed_records WHERE tenant_id=? AND table_name=?',(tenant,table))} for table in TABLES}
    protected={table:set() for table in TABLES}
    # Untracked children/relationships must never cascade away.
    references={'leads': [('messages','lead_id'),('tasks','lead_id'),('appointments','lead_id'),('deals','lead_id'),('outbox','lead_id'),('conversation_controls','lead_id'),('consent_events','lead_id'),('adviser_cases','lead_id'),('enterprise_artifacts','lead_id'),('chat_sessions','lead_id'),('telegram_actions','lead_id'),('telegram_contacts','lead_id')],
                'properties':[('appointments','property_id'),('deals','property_id')],
                'users':[('appointments','agent_id'),('leads','assigned_to')]}
    for parent,children in references.items():
        for table,field in children:
            key='lead_id' if table in ('conversation_controls','telegram_contacts') else 'token_hash' if table=='chat_sessions' else 'id'
            for row in c.execute(f'SELECT {key},{field} FROM {table} WHERE tenant_id=?',(tenant,)):
                if row[0] not in owned.get(table,set()) and row[1] in owned[parent]:protected[parent].add(row[1])
    # Keep generated users assigned to retained leads or appointments.
    for lead in protected['leads']:
        assigned=c.execute('SELECT assigned_to FROM leads WHERE tenant_id=? AND id=?',(tenant,lead)).fetchone()[0]
        protected['users'].add(assigned)
    for table in TABLES:
        key='lead_id' if table=='conversation_controls' else 'id'
        for identifier in owned[table]-protected[table]:
            c.execute(f'DELETE FROM {table} WHERE tenant_id=? AND {key}=?',(tenant,identifier))
            c.execute('DELETE FROM demo_seed_records WHERE tenant_id=? AND table_name=? AND record_id=?',(tenant,table,identifier))
    c.execute('DELETE FROM demo_datasets WHERE tenant_id=?',(tenant,))
    return sum(len(v) for v in protected.values())
