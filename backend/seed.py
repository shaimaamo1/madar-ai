import json
from datetime import datetime, timedelta, timezone

from .db import now, uid
from .domain import create_lead


def seed_demo(c, tenant, admin, password_hash):
    agents = [admin]
    for name in ['Omar Hassan', 'Nour Khaled']:
        user = uid()
        agents.append(user)
        c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)', (user, tenant, name.split()[0].lower()+'@demo.invalid', name, 'agent', password_hash, 1))
    props = [('Palm Residence', 'New Cairo', 'Apartment', 'buy', 4800000, 185, 3, ['Pool', 'Parking', 'Security']),
             ('Garden Terrace', 'New Cairo', 'Apartment', 'buy', 3650000, 145, 2, ['Garden', 'Parking']),
             ('Zayed Signature Villa', 'Sheikh Zayed', 'Villa', 'buy', 12500000, 340, 4, ['Garden', 'Pool', 'Security']),
             ('Marina Studio', 'Dubai', 'Apartment', 'rent', 68000, 76, 1, ['Pool', 'Gym']),
             ('Coastal Retreat', 'North Coast', 'Apartment', 'buy', 6200000, 160, 3, ['Beach', 'Pool']),
             ('Cairo Business Suite', 'New Cairo', 'Office', 'rent', 42000, 120, 0, ['Parking', 'Security'])]
    prop_ids = []
    for title, location, kind, intent, price, size, beds, amenities in props:
        p = uid()
        prop_ids.append(p)
        c.execute('INSERT INTO properties VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (p, tenant, title, location, kind, intent, price, size, beds, json.dumps(amenities), 'Available', 'Fictional demonstration listing. Prices are illustrative in tenant currency.', '', now()))
    names = [('Laila Mostafa', 'website', 5000000, 'New Cairo', 3, 'Qualified'),
             ('Ahmed Tarek', 'whatsapp', 14000000, 'Sheikh Zayed', 4, 'Viewing'),
             ('Mariam Adel', 'facebook', 4000000, 'New Cairo', 2, 'New'),
             ('Youssef Ali', 'telegram', 6000000, 'North Coast', 3, 'Negotiation'),
             ('Salma Fathy', 'website', 5000000, 'New Cairo', 3, 'Won'),
             ('Karim Nabil', 'email', 2800000, 'New Cairo', 2, 'Lost')]
    for i, (name, source, budget, location, beds, stage) in enumerate(names):
        lead, _ = create_lead(c, tenant, {'name': name, 'source': source, 'email': f'customer{i}@demo.invalid', 'budget': budget, 'location': location, 'bedrooms': beds, 'property_type': 'Villa' if beds == 4 else 'Apartment', 'consent': True})
        updated = (datetime.now(timezone.utc) - timedelta(hours=72 if i == 3 else i * 3)).isoformat()
        c.execute('UPDATE leads SET stage=?,updated_at=? WHERE id=? AND tenant_id=?', (stage, updated, lead['id'], tenant))
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)', (uid(), tenant, lead['id'], 'inbound', source, 'I am looking for a property in ' + location, '', updated))
        if stage in ('Won', 'Lost'):
            c.execute('INSERT INTO deals VALUES(?,?,?,?,?,?,?,?,?)', (uid(), tenant, lead['id'], prop_ids[0], 4800000 if stage == 'Won' else budget, 96000 if stage == 'Won' else 0, stage, 'Budget mismatch' if stage == 'Lost' else '', now()))
    return prop_ids
