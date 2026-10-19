"""Build the DotA knowledge base the MCP server uses: heroes (with skills, orders, cooldowns, mana)
and shop items (token unit id, name, price, shop), read straight from the map's object data.

Usage: python -I build_kb.py <wc3_dir> <map.w3x> <out.json>
"""
import glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mpq import MPQ
from wc3data import read_slk, read_profile, clean, first

wc3, map_path, out_path = sys.argv[1:4]
m = MPQ(map_path)
listfile = m.read('(listfile)').decode('utf-8', 'replace').replace('\r', '').split('\n')


def mread(name):
    d = m.read(name)
    if d is None:
        raise SystemExit('missing in map: ' + name)
    return d


# ---- profiles (.txt) from the map, then the game's own files as fallback for base data
prof = {}
for n in listfile:
    if re.match(r'(?i)^Units\\.*(Func|Strings)\.txt$', n):
        read_profile(mread(n), prof)
base_prof = {}
for arc in ('War3Patch.mpq', 'War3x.mpq', 'war3.mpq'):
    a = MPQ(os.path.join(wc3, arc))
    for kind in ('Human', 'Orc', 'Undead', 'NightElf', 'Neutral', 'Common', 'Campaign', 'Item'):
        d = a.read('Units\\%sAbilityFunc.txt' % kind)
        if d:
            read_profile(d, base_prof)

unit_abil = read_slk(mread('Units\\UnitAbilities.slk'))
unit_bal = read_slk(mread('Units\\UnitBalance.slk'))
abil = read_slk(mread('Units\\AbilityData.slk'))


# base abilities whose order string is built into the engine (absent from the data files)
BUILTIN_ORDERS = {'ANfb': 'firebolt', 'AHdr': 'drain', 'AHca': 'coldarrows', 'ANcr': 'chemicalrage',
                  'Afae': 'faeriefire', 'Acri': 'cripple', 'ANso': 'soulburn', 'ANab': 'acidbomb'}


def order_of(aid):
    """Order string used to cast ability aid (None for passives)."""
    code = abil.get(aid, {}).get('code', aid)
    if code == 'ANcl':                       # Channel: order comes from DataF ('Base Order ID')
        o = abil.get(aid, {}).get('DataF1')
        return o if o and o != '-' else 'channel'
    for src in (prof.get(aid, {}), base_prof.get(code, {})):
        low = {k.lower(): v for k, v in src.items()}
        o = first(low.get('order') or low.get('orderon') or '')
        if o:
            return o
    return BUILTIN_ORDERS.get(code)


TARGS = {'_': '', '-': ''}


def num(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def ability(aid):
    a = abil.get(aid, {})
    p = prof.get(aid, {})
    lv = int(num(a.get('levels')) or 1)
    desc = clean(first(p.get('Researchubertip') or p.get('Ubertip') or ''))
    desc = re.sub(r'<[^>]*>', '?', desc)
    cast = None
    if a.get('code') == 'ANcl':              # Channel: DataB is the target type
        cast = {0: 'no target', 1: 'unit', 2: 'point', 3: 'unit or point'}.get(int(num(a.get('DataB1')) or 0))
    return {
        'cast': cast,
        'id': aid,
        'name': clean(first(p.get('Name', aid))),
        'hotkey': clean(p.get('Researchhotkey') or p.get('Hotkey') or ''),
        'base': a.get('code', aid),
        'order': order_of(aid),
        'levels': lv,
        'cooldown': [num(a.get('Cool%d' % i)) for i in range(1, min(lv, 4) + 1)],
        'mana': [num(a.get('Cost%d' % i)) for i in range(1, min(lv, 4) + 1)],
        'range': [num(a.get('Rng%d' % i)) for i in range(1, min(lv, 4) + 1)],
        'targets': a.get('targs1', ''),
        'desc': desc[:300],
    }


def is_hero(uid):
    return unit_abil.get(uid, {}).get('heroAbilList', '_') not in ('_', '', '-')


# ---- taverns, selectors, item shops
heroes, taverns, shops, items = {}, {}, {}, {}
for uid, p in prof.items():
    sold = [s for s in (p.get('Sellunits') or '').split(',') if s]
    if not sold:
        continue
    name = clean(p.get('Name', uid))
    hs = [s for s in sold if is_hero(s)]
    if hs:
        taverns[uid] = {'name': name, 'heroes': hs}
        for h in hs:
            heroes.setdefault(h, {'taverns': []})['taverns'].append(uid)
    elif sold == ['h06N']:
        continue                             # per-hero draft selector; mapped from the script below
    elif len(sold) >= 6:                     # item shops sell token units the map turns into items
        shops[uid] = {'name': name, 'items': sold}
        for s in sold:
            items.setdefault(s, {'shops': []})['shops'].append(uid)

for h, e in heroes.items():
    p = prof.get(h, {})
    b = unit_bal.get(h, {})
    e.update({
        'id': h,
        'name': clean(first(p.get('Name', h))),
        'proper': clean(first(p.get('Propernames', ''))),
        'primary': b.get('Primary', ''),
        'str': num(b.get('STR')), 'agi': num(b.get('AGI')), 'int': num(b.get('INT')),
        'str+': num(b.get('STRplus')), 'agi+': num(b.get('AGIplus')), 'int+': num(b.get('INTplus')),
        'skills': [ability(a) for a in unit_abil[h]['heroAbilList'].split(',') if a and a != '_'],
    })

for t, e in items.items():
    p = prof.get(t, {})
    tip = clean(first(p.get('Ubertip') or p.get('Tip') or ''))
    e.update({
        'id': t,
        'name': clean(first(p.get('Name', t))),
        'cost': int(num(unit_bal.get(t, {}).get('goldcost')) or 0),
        'desc': tip[:240],
        'shop_names': sorted({shops[s]['name'] for s in e['shops']}),
    })

for t, e in items.items():
    raw_tip = first(prof.get(t, {}).get('Ubertip') or '')
    lines = [clean(x) for x in raw_tip.split('|n')]
    req = []
    if any('Requires:' in x for x in lines):
        for x in lines[next(i for i, x in enumerate(lines) if 'Requires:' in x) + 1:]:
            if not x:
                break
            req.append(x)
    e['requires'] = req[:6]
    e['buyable'] = e['cost'] > 0

# names for inventory items (I-codes) and every unit type (creeps, towers, summons...)
item_prof = {}
for n in listfile:
    if re.match(r'(?i)^Units\\Item(Strings|Func)\.txt$', n):
        read_profile(mread(n), item_prof)
item_names = {k: clean(first(v['Name'])) for k, v in item_prof.items() if v.get('Name') and len(k) == 4}
unit_names = {k: clean(first(v['Name'])) for k, v in prof.items() if v.get('Name') and len(k) == 4 and k not in item_names}
abil_names = {k: clean(first(v['Name'])) for k, v in prof.items() if v.get('Name') and k in abil}
abil_names['Aamk'] = 'Attribute Bonus'
for h in heroes.values():
    for s in h['skills']:
        if s['name'] in ('', s['id']) or s['base'] == 'Aamk':
            s['name'] = abil_names.get(s['id'], 'Attribute Bonus' if s['base'] == 'Aamk' else s['id'])

kb = {'map': os.path.basename(map_path), 'heroes': sorted(heroes.values(), key=lambda h: h['name']),
      'taverns': taverns, 'shops': shops, 'items': sorted(items.values(), key=lambda i: i['name']),
      'item_names': item_names, 'unit_names': unit_names}
os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
json.dump(kb, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
castable = sum(1 for h in heroes.values() for s in h['skills'] if s['order'])
print('heroes %d (skills %d, castable %d) | taverns %d | shops %d | items %d' % (
    len(heroes), sum(len(h['skills']) for h in heroes.values()), castable, len(taverns), len(shops), len(items)))
for h in kb['heroes'][:5]:
    print(' ', h['id'], h['name'], '/', h['proper'], h['primary'], [(s['name'], s['hotkey'], s['order']) for s in h['skills']])
for i in kb['items'][:8]:
    print(' ', i['id'], i['name'], i['cost'], i['shop_names'])
