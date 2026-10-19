"""Port Monkey King and Mars (from DracoL1ch DotA 7.03R11) into the DotA 6.88f AI Superpower map.
Usage: python -I build_port.py <target.w3x> <source.w3x> <assets_dir> <pz_heroes.j> <out.w3x> [--test] [--name NAME]
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server', 'tools'))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
from mpq import MPQ
from wc3data import read_slk, read_profile
from wc3edit import slk_append, profile_append, profile_set, write_mpq

args = sys.argv[1:]
TEST = '--test' in args
if TEST:
    args.remove('--test')
NAME = 'DotA AI 6.88 MK+Mars'
STAGE = 9
UNITS = None
PARTS = 'LVBRPGE'
if '--parts' in args:
    i = args.index('--parts'); PARTS = args[i + 1]; del args[i:i + 2]
if '--units' in args:
    i = args.index('--units'); UNITS = set(args[i + 1].split(',')); del args[i:i + 2]
if '--stage' in args:
    i = args.index('--stage'); STAGE = int(args[i + 1]); del args[i:i + 2]
if '--name' in args:
    i = args.index('--name'); NAME = args[i + 1]; del args[i:i + 2]
TGT, SRC, ASSETS, JFILE, OUT = args
WC3 = os.environ.get('WC3_DIR', r'C:\Program Files (x86)\Warcraft III')
if os.path.exists(OUT):
    sys.exit('refusing to overwrite ' + OUT)

tm = MPQ(TGT)
names = [n for n in tm.read('(listfile)').decode('utf-8', 'replace').replace('\r', '').split('\n') if n.strip()]
files = {}
order = []
for n in names:
    if n in ('(listfile)', '(attributes)', '(signature)'):
        continue
    d = tm.read(n)
    if d is None:
        sys.exit('listed but unreadable: ' + n)
    files[n] = d
    order.append(n)
print('target files:', len(files))

# ---------------- source strings (tooltips)
sm = MPQ(SRC)
src_str = read_profile(sm.read('Units\\OrcAbilityStrings.txt'))
def S(sid, key):
    v = src_str[sid][key]
    return v

def strip_scepter(s):
    s = re.sub(r'\|n\|n\|cFFFFFC01Scepter Upgrade?able:.*?\|r', '', s)
    s = s.replace(' (|cFFFFFC01Scepter upgradable|r)', '')
    return s

def tips(sid, nlev=4):
    out = [('Name', S(sid, 'name')), ('Tip', S(sid, 'tip')), ('Ubertip', strip_scepter(S(sid, 'ubertip')))]
    if 'researchtip' in src_str[sid]:
        out.append(('Researchtip', S(sid, 'researchtip')))
        out.append(('Researchubertip', strip_scepter(S(sid, 'researchubertip'))))
    return out

# ---------------- object data rows
def lv(fmt, vals):
    return {fmt % (i + 1): v for i, v in enumerate(vals)}

def ancl(aid, levels, cool, cost, rng, area, dataA, dataB, dataC, order, req=1, skip=None, targs=''):
    r = {'alias': aid, 'code': 'ANcl', 'levels': levels, 'reqLevel': req}
    if skip:
        r['levelSkip'] = skip
    for i in range(levels):
        L = i + 1
        if targs:
            r['targs%d' % L] = targs
        r['Cool%d' % L] = cool[i]
        r['Cost%d' % L] = cost[i]
        r['Rng%d' % L] = rng
        if area:
            r['Area%d' % L] = area
        r['DataA%d' % L] = dataA
        r['DataB%d' % L] = dataB
        r['DataC%d' % L] = dataC
        r['DataF%d' % L] = order
    return r

def simple(aid, code, levels, per_level):
    r = {'alias': aid, 'code': code, 'levels': levels, 'reqLevel': 1}
    for i in range(levels):
        for k, v in per_level(i + 1).items():
            r['%s%d' % (k, i + 1)] = v
    return r

STUN_T = 'air,enemy,ground,neutral,organic,mechanical'
abil_rows = [
    ancl('AZ02', 4, [22] * 4, [100] * 4, 1200, 0, 0, 2, 1, 'avengerform'),
    ancl('AZ03', 4, [1] * 4, [0] * 4, 1000, 0, 0, 2, 1, 'auravampiric'),
    ancl('AZ04', 4, [19, 17, 15, 13], [100] * 4, 99999, 375, 1.6, 2, 3, 'autodispel'),
    simple('AZ05', 'AEev', 4, lambda L: {'DataA': 0}),
    simple('AZ06', 'AUav', 4, lambda L: {'targs': 'self', 'Area': 100, 'DataA': round(0.15 * L, 2), 'BuffID': 'BUav'}),
    simple('AZ07', 'AItg', 4, lambda L: {'DataA': 10 + 30 * L}),
    ancl('AZ08', 3, [130, 110, 90], [100] * 3, 550, 1050, 0, 2, 3, 'ancestralspirittarget', req=6, skip=5),
    simple('AZ09', 'AId1', 3, lambda L: {'DataA': 6 + 6 * L}),
    ancl('AZ10', 4, [14] * 4, [100] * 4, 9999, 0, 0, 2, 1, 'shockwave'),
    ancl('AZ11', 4, [16, 14, 12, 10], [65, 70, 75, 80], 9999, 0, 0, 2, 1, 'blizzard'),
    simple('AZ12', 'AEev', 4, lambda L: {'DataA': 0}),
    ancl('AZ13', 3, [90, 75, 60], [200] * 3, 400, 550, 0, 2, 3, 'breathoffire', req=6, skip=5),
    simple('AZ14', 'AHtb', 4, lambda L: {'targs': STUN_T, 'Dur': [0.7, 1.0, 1.3, 1.6][L - 1], 'HeroDur': [0.7, 1.0, 1.3, 1.6][L - 1], 'Cool': 0, 'Cost': 0, 'Rng': 9999, 'DataA': 0, 'BuffID': 'BPSE'}),
    simple('AZ17', 'AHtb', 4, lambda L: {'targs': STUN_T, 'Dur': [1.6, 2.0, 2.4, 2.8][L - 1], 'HeroDur': [1.6, 2.0, 2.4, 2.8][L - 1], 'Cool': 0, 'Cost': 0, 'Rng': 9999, 'DataA': 0, 'BuffID': 'BPSE'}),
    simple('AZ18', 'AHtb', 1, lambda L: {'targs': STUN_T, 'Dur': 4.0, 'HeroDur': 4.0, 'Cool': 0, 'Cost': 0, 'Rng': 9999, 'DataA': 0, 'BuffID': 'BPSE'}),
    simple('AZ15', 'Aslo', 4, lambda L: {'targs': 'air,enemy,ground,neutral,organic', 'Dur': 4.0, 'HeroDur': 4.0, 'Cool': 0, 'Cost': 0, 'Rng': 9999, 'DataA': round(0.2 * L, 2), 'DataB': 0, 'BuffID': 'Bslo'}),
    simple('AZ19', 'Aslo', 1, lambda L: {'targs': 'air,enemy,ground,neutral,organic', 'Dur': 1.5, 'HeroDur': 1.5, 'Cool': 0, 'Cost': 0, 'Rng': 9999, 'DataA': 0.4, 'DataB': 0, 'BuffID': 'Bslo'}),
    simple('AZ16', 'AIlf', 1, lambda L: {'DataA': 2000}),
]

CB = 'ReplaceableTextures\\CommandButtons\\'
PB = 'ReplaceableTextures\\PassiveButtons\\'
abil_prof = [
    ('AZ02', [('Art', CB + 'BTNMKStrike.blp'), ('Researchart', CB + 'BTNMKStrike.blp'), ('Buttonpos', '0,2'), ('Researchbuttonpos', '0,0'),
              ('Hotkey', 'B'), ('Researchhotkey', 'B'), ('Animnames', 'attack,slam')] + tips('A005')),
    ('AZ03', [('Art', CB + 'BTNMKTree.blp'), ('Researchart', CB + 'BTNMKTree.blp'), ('Buttonpos', '1,2'), ('Researchbuttonpos', '1,0'),
              ('Hotkey', 'T'), ('Researchhotkey', 'T'), ('Animnames', 'spell')] + tips('A006')),
    ('AZ04', [('Art', CB + 'BTNMKTreeSpring.blp'), ('Buttonpos', '1,1'), ('Hotkey', 'R'), ('Animnames', 'spell,channel')] + tips('A008')),
    ('AZ05', [('Art', PB + 'PASSBTNMKJingu.blp'), ('Researchart', CB + 'BTNMKJingu.blp'), ('Buttonpos', '2,2'), ('Researchbuttonpos', '2,0'),
              ('Researchhotkey', 'G')] + tips('A00G')),
    ('AZ06', [('Name', 'Jingu Mastery lifesteal'), ('Art', PB + 'PASSBTNMKJingu.blp'), ('Buttonpos', '0,-11'), ('Targetart', ''),
              ('Buffart', PB + 'PASSBTNMKJingu.blp')]),
    ('AZ07', [('Name', 'Jingu Mastery damage')]),
    ('AZ08', [('Art', CB + 'BTNMKUlti.blp'), ('Researchart', CB + 'BTNMKUlti.blp'), ('Buttonpos', '3,2'), ('Researchbuttonpos', '3,0'),
              ('Hotkey', 'W'), ('Researchhotkey', 'W'), ('Animnames', 'stand,ready'), ('CasterArt', 'H\\MK\\HeroMonkeyking_R3_Gather.mdx')] + tips('A00O', 3)),
    ('AZ09', [('Name', "Wukong's Command armor")]),
    ('AZ10', [('Art', CB + 'MarsSpear.blp'), ('Researchart', CB + 'MarsSpear.blp'), ('Buttonpos', '0,2'), ('Researchbuttonpos', '0,0'),
              ('Hotkey', 'E'), ('Researchhotkey', 'E'), ('Animnames', 'attack')] + tips('A49I')),
    ('AZ11', [('Art', CB + 'MarsRebuke.blp'), ('Researchart', CB + 'MarsRebuke.blp'), ('Buttonpos', '1,2'), ('Researchbuttonpos', '1,0'),
              ('Hotkey', 'R'), ('Researchhotkey', 'R'), ('Animnames', 'spell')] + tips('A49J')),
    ('AZ12', [('Art', PB + 'PASMarsBulwark.blp'), ('Researchart', CB + 'MarsBulwark.blp'), ('Buttonpos', '2,2'), ('Researchbuttonpos', '2,0'),
              ('Researchhotkey', 'W')] + tips('A49H')),
    ('AZ13', [('Art', CB + 'MarsArenaOfBlood.blp'), ('Researchart', CB + 'MarsArenaOfBlood.blp'), ('Buttonpos', '3,2'), ('Researchbuttonpos', '3,0'),
              ('Hotkey', 'B'), ('Researchhotkey', 'B'), ('Animnames', 'victory')] + tips('A49M', 3)),
    ('AZ14', [('Name', 'MK stun'), ('Missileart', ''), ('Missilespeed', '20000'), ('Missilearc', '0')]),
    ('AZ17', [('Name', 'Spear stun'), ('Missileart', ''), ('Missilespeed', '20000'), ('Missilearc', '0')]),
    ('AZ18', [('Name', 'Fall stun'), ('Missileart', ''), ('Missilespeed', '20000'), ('Missilearc', '0')]),
    ('AZ15', [('Name', 'Primal Spring slow'), ('Missileart', ''), ('Missilespeed', '20000')]),
    ('AZ19', [('Name', "God's Rebuke slow"), ('Missileart', ''), ('Missilespeed', '20000')]),
    ('AZ16', [('Name', 'Bulwark buffer')]),
]
# Tree Dance: the "damage puts it on cooldown" rule is not implemented
for sid, kv in abil_prof:
    for i, (k, v) in enumerate(kv):
        if sid == 'AZ03' and k in ('Ubertip', 'Researchubertip'):
            kv[i] = (k, re.sub(r' Taking damage from player controlled units or Roshan while on the ground puts Tree Dance on 3 seconds cooldown\.', '', v))

# units
def tgt_row(table, uid):
    rows = read_slk(files['Units\\%s.slk' % table])
    return dict(rows[uid])

src_rows = {t: read_slk(sm.read('Units\\%s.slk' % t)) for t in ('UnitData', 'UnitBalance', 'UnitUI', 'UnitAbilities', 'UnitWeapons')}
def src_row(table, uid, new=None):
    r = {k: v for k, v in src_rows[table][uid].items() if v != ''}
    if new:
        first = next(iter(r))
        r[first] = new
    return r

unit_rows = {t: [] for t in ('UnitData', 'UnitBalance', 'UnitUI', 'UnitAbilities', 'UnitWeapons')}
for hid, pts in (('H0MK', 113), ('HMRS', 114)):
    r = src_row('UnitData', hid); r['points'] = pts; r['race'] = 'human'; r['cargoSize'] = 1
    unit_rows['UnitData'].append(r)
    r = src_row('UnitBalance', hid); r['upgrades'] = 'R00L,R00M'; r['bldtm'] = 55; r['reptm'] = 55; r['tilesets'] = '*'
    unit_rows['UnitBalance'].append(r)
    r = src_row('UnitUI', hid)
    if hid == 'H0MK':
        r.update({'shadowW': 120, 'shadowH': 120, 'shadowX': 60, 'shadowY': 60})
    else:
        r['file'] = 'H\\Mars\\MarsBasic.mdx'
    r['teamColor'] = -1
    unit_rows['UnitUI'].append(r)
    unit_rows['UnitAbilities'].append({'unitAbilID': hid, 'auto': '_', 'abilList': 'AInv,A1FG',
                                       'heroAbilList': 'AZ02,AZ03,AZ05,AZ08,Aamk' if hid == 'H0MK' else 'AZ10,AZ11,AZ12,AZ13,Aamk'})
    unit_rows['UnitWeapons'].append(src_row('UnitWeapons', hid))
for sel, model, scale in (('hZMK', 'H\\MK\\MonkeyKing.mdx', 1.0), ('hZMR', 'H\\Mars\\MarsBasic.mdx', 1.5)):
    for t in unit_rows:
        r = tgt_row(t, 'h03Z')
        r[next(iter(r))] = sel
        r = {k: v for k, v in r.items() if v != ''}
        if t == 'UnitUI':
            r['file'] = model; r['modelScale'] = scale; r['name'] = 'Custom_' + sel
        unit_rows[t].append(r)
DUMMY_ABIL = {'eZ01': 'A04R,Aloc', 'eZ02': 'A04R,Aloc', 'eZ03': 'A04R,Aloc', 'eZ04': 'A04R,Aloc', 'eZ05': 'Ahrl,Aloc'}
DUMMY_MODEL = {'eZ01': '_', 'eZ02': 'H\\MK\\MonkeyKing.mdx', 'eZ03': 'H\\Mars\\ArenaOfBloodWallElement.mdx',
               'eZ04': 'H\\Mars\\NewMarsSpear.mdx', 'eZ05': '_'}
# dummies are copies of the map's own vision dummy (o00G), with only the needed fields changed
for did in ('eZ01', 'eZ02', 'eZ03', 'eZ04', 'eZ05'):
    fly = did in ('eZ01', 'eZ04')
    over = {
        'UnitData': {'movetp': 'fly' if fly else 'foot', 'moveHeight': 90 if did == 'eZ04' else 0, 'turnRate': 3},
        'UnitBalance': {'spd': 100 if did == 'eZ05' else 0, 'manaN': 1000, 'mana0': 1000},
        'UnitUI': {'file': DUMMY_MODEL[did], 'name': 'Custom_' + did, 'modelScale': 1.2 if did == 'eZ03' else 1},
        'UnitAbilities': {'abilList': DUMMY_ABIL[did]},
        'UnitWeapons': {'castpt': 0, 'castbsw': 0},
    }
    for t in unit_rows:
        r = tgt_row(t, 'o00G')
        r[next(iter(r))] = did
        r = {k: v for k, v in r.items() if v != ''}
        r.update(over[t])
        unit_rows[t].append(r)

hero_tip = {k: strip_scepter(v) for k, v in (('H0MK', S('H0MK', 'ubertip')), ('HMRS', S('HMRS', 'ubertip')))}
unit_prof = [
    ('H0MK', [('Name', '"Monkey King"'), ('Propernames', 'Sun Wukong'), ('Tip', '"Monkey King"'), ('Ubertip', hero_tip['H0MK']),
              ('Revivetip', 'Revive Monkey King'), ('Awakentip', 'Awaken Monkey King'), ('Description', 'Monkey King'),
              ('Art', CB + 'BTNMKHero.blp'), ('ScoreScreenIcon', CB + 'BTNMKHero.blp'), ('Buttonpos', '2,1'), ('Hotkey', '')]),
    ('HMRS', [('Name', '"Mars"'), ('Propernames', 'Mars,God of War,Ares'), ('Tip', '"Mars"'), ('Ubertip', hero_tip['HMRS']),
              ('Revivetip', 'Revive Mars'), ('Awakentip', 'Awaken Mars'), ('Description', 'Mars'),
              ('Art', CB + 'BTNTheCaptain.blp'), ('ScoreScreenIcon', CB + 'BTNTheCaptain.blp'), ('Buttonpos', '0,1'), ('Hotkey', '')]),
    ('hZMK', [('Name', '"Monkey King"'), ('Art', CB + 'BTNSelectHero.blp'), ('Sellunits', 'h06N')]),
    ('hZMR', [('Name', '"Mars"'), ('Art', CB + 'BTNSelectHero.blp'), ('Sellunits', 'h06N')]),
    ('eZ01', [('Name', 'PZ dummy')]), ('eZ02', [('Name', 'Monkey Soldier')]), ('eZ03', [('Name', 'Ash Legion')]),
    ('eZ04', [('Name', 'Spear of Mars')]), ('eZ05', [('Name', 'PZ tree check')]),
]

if UNITS is not None:
    for t in unit_rows:
        unit_rows[t] = [r for r in unit_rows[t] if next(iter(r.values())) in UNITS]
# ---------------- apply object data
if STAGE >= 1:
    for t, rows in unit_rows.items():
        files['Units\\%s.slk' % t] = slk_append(files['Units\\%s.slk' % t], rows)
    files['Units\\AbilityData.slk'] = slk_append(files['Units\\AbilityData.slk'], abil_rows)
    files['Units\\CampaignAbilityStrings.txt'] = profile_append(files['Units\\CampaignAbilityStrings.txt'], abil_prof)
    files['Units\\CampaignUnitStrings.txt'] = profile_append(files['Units\\CampaignUnitStrings.txt'], unit_prof)
    files['Units\\NeutralUnitFunc.txt'] = profile_set(files['Units\\NeutralUnitFunc.txt'], 'n007', 'Sellunits', lambda v: v.rstrip() + ',H0MK')
    files['Units\\NeutralUnitFunc.txt'] = profile_set(files['Units\\NeutralUnitFunc.txt'], 'n0LJ', 'Sellunits', lambda v: v.rstrip() + ',HMRS')

# ---------------- assets
if STAGE >= 2:
    added = 0
    for root, _, fs in os.walk(ASSETS):
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), ASSETS)
            if rel in files or rel.lower() in (n.lower() for n in files):
                print('asset already in map, keeping map copy:', rel)
                continue
            files[rel] = open(os.path.join(root, f), 'rb').read()
            order.append(rel)
            added += 1
    print('assets added:', added)

# ---------------- script
if STAGE >= 3:
    sname = next(n for n in files if n.lower() in ('scripts\\war3map.j', 'war3map.j'))
    print('script file:', sname)
    raw = files[sname]
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw[3:].decode('utf-8') if bom else raw.decode('utf-8')
    EOL = '\r\n' if '\r\n' in text else '\n'
    code = open(JFILE, encoding='utf-8').read().replace('\r\n', '\n')
    parts = dict(re.findall(r'//@(\w+)\n(.*?)(?=//@\w+\n|\Z)', code, re.S))
    GLOB, FUNCS = parts['GLOBALS'].strip('\n'), parts['FUNCS'].strip('\n')
    if TEST:
        GLOB = GLOB.replace('integer PZPickTest=0', 'integer PZPickTest=1').replace('boolean PZDebug=false', 'boolean PZDebug=true')
        # test build: every slot except Player 1 is a computer, so -loadfile starts a game with 9 bots
        sys.path.insert(0, HERE)
        from w3i import set_types
        FKt = {n.lower(): n for n in files}
        files[FKt['war3map.w3i']] = set_types(files[FKt['war3map.w3i']], {n: 2 for n in (2, 3, 4, 5, 7, 8, 9, 10, 11)})

    def known_natives():
        ns = set()
        for arc in ('War3Patch.mpq', 'War3x.mpq', 'war3.mpq'):
            a = MPQ(os.path.join(WC3, arc))
            for p in ('Scripts\\common.j', 'Scripts\\Blizzard.j'):
                d = a.read(p)
                if d:
                    ns |= set(re.findall(r'^\s*(?:constant\s+)?(?:native|function)\s+(\w+)', d.decode('latin-1'), re.M))
        return ns
    known = known_natives()
    map_funcs = set(re.findall(r'^function (\w+)', text, re.M))
    def lint(src, label):
        depth = []
        defined = set()
        for ln, line in enumerate(src.split('\n'), 1):
            s = line.strip()
            if s.startswith('//') or not s:
                continue
            mm = re.match(r'function (\w+)', s)
            if mm:
                defined.add(mm.group(1)); depth.append('function')
            for kw, close in (('if', 'endif'), ('loop', 'endloop')):
                if re.match(r'%s\b' % kw, s): depth.append(kw)
                if s == close:
                    if not depth or depth.pop() != kw: sys.exit('%s:%d unbalanced %s' % (label, ln, close))
            if s == 'endfunction':
                if not depth or depth.pop() != 'function': sys.exit('%s:%d unbalanced endfunction' % (label, ln))
            body = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
            body = re.sub(r"'[^']{4}'", '0', body)
            for call in re.findall(r'\b([A-Za-z_]\w*)\s*\(', body):
                if call in ('if', 'not', 'and', 'or', 'function', 'return', 'set', 'call', 'local', 'exitwhen', 'elseif'):
                    continue
                if call not in known and call not in map_funcs and call not in defined:
                    sys.exit('%s:%d unknown function %s' % (label, ln, call))
            for ref in re.findall(r'function (\w+)\)', body):
                if ref not in defined and ref not in map_funcs:
                    sys.exit('%s:%d function reference before definition: %s' % (label, ln, ref))
        if depth: sys.exit('%s: unclosed %s' % (label, depth))
    lint(FUNCS, 'FUNCS')
    ours = set(re.findall(r'^\s*\w+(?:\s+array)?\s+(\w+)', GLOB, re.M)) | set(re.findall(r'^function (\w+)', FUNCS, re.M))
    clash = sorted(ours & set(re.findall(r'\b[A-Za-z_]\w*\b', text)))
    if clash:
        sys.exit('names already used by the map: %s' % clash)
    gl = text[:text.index('endglobals')]
    gnames = set(re.findall(r'^\s*(?:constant\s+)?\w+(?:\s+array)?\s+(\w+)', gl, re.M))
    locs = set(re.findall(r'^local\s+\w+\s+(\w+)', FUNCS, re.M))
    locs |= {x for a in re.findall(r'takes (.*?) returns', FUNCS) if a != 'nothing' for x in re.findall(r'\w+\s+(\w+)', a)}
    if locs & (gnames | ours):
        sys.exit('locals/parameters shadow globals: %s' % sorted(locs & (gnames | ours)))
    for g in ('J', 'K34', 'MI4', 'K64', 'MH4', 'K54', 'HM4', 'HW4'):
        if not re.search(r'^\s*\w+(\s+array)?\s+%s\b' % g, gl, re.M):
            sys.exit('map global missing: ' + g)

    def sub_once(pat, rep, label, count=1):
        global text
        new, n = re.subn(pat, rep, text, flags=re.M)
        if n != count:
            sys.exit('%s: expected %d match(es), found %d' % (label, count, n))
        text = new

    # hero table (LX7)
    mk_tips = ['Boundless Strike stuns everything in a long line - line up several enemy heroes before you swing.',
               'Tree Dance lets you hop between trees; Primal Spring from a tree hits harder the longer you channel it.',
               'Jingu Mastery charges after four hits on the same hero: the four charged attacks give big bonus damage and lifesteal.',
               "Wukong's Command soldiers only attack heroes. Stay inside the circle to keep the bonus armor.",
               'Items that give attack damage and agility make both Boundless Strike and the soldiers stronger.']
    mars_tips = ['Spear of Mars pins a hero to a tree, cliff or building - aim so the target flies into an obstacle.',
                 "God's Rebuke hits everything in front of you and knocks it back; use it to push enemies into your Arena.",
                 'Bulwark blocks a large part of physical attacks from the front and sides. Face your attackers.',
                 'Arena of Blood traps enemies inside; heroes near the edge are hit by the Ash Legion spears.',
                 'Strength items help Mars stay in the fight, and his spells scale with his attack damage.']
    def hero_block(idx, hid, sel, icon, anim, scale, tl):
        b = ['set K34[%d]=%s' % (idx, "'%s'" % hid), 'set MI4[%d]=%s' % (idx, "'%s'" % sel), 'set K64[%d]=%s' % (idx, "'%s'" % hid),
             'set MH4[%d]="%s"' % (idx, icon.replace('\\', '\\\\')), 'call XY7(K34[%d],"%s")' % (idx, anim),
             'call XU7(K34[%d],%s,MI4[%d])' % (idx, scale, idx)]
        for arr, t in zip(('MJ4', 'MK4', 'MM4', 'MN4', 'MO4'), tl):
            b.append('set %s[%d]="%s"' % (arr, idx, t.replace('"', "'")))
        return EOL.join(b)
    blk = hero_block(113, 'H0MK', 'hZMK', CB + 'BTNMKHero.blp', 'stand victory', '1.', mk_tips) + EOL + \
          hero_block(114, 'HMRS', 'hZMR', CB + 'BTNTheCaptain.blp', 'stand victory', '1.5', mars_tips)
    # LX7 is huge and sits at a 1.27b script-compiler limit: keep it the same size and call a separate function
    if 'L' in PARTS:
        sub_once(r'^set K54=112(?=\r?$)', 'call PZHeroTable()', 'hero table K54')
        lx = text.index(EOL + 'function LX7 takes nothing returns nothing' + EOL)
        text = text[:lx] + EOL + 'function PZHeroTable takes nothing returns nothing' + EOL + blk + EOL + 'set K54=114' + EOL + \
               'endfunction' + text[lx:]

    # AI ability tables (V5)
    v5 = ["set HM4[113]='AZ02'", "set HN4[113]='AZ05'", "set HO4[113]='AZ03'", "set HP4[113]='AZ08'",
          'set HW4[113]="avengerform"', 'set HX4[113]="passive"', 'set HY4[113]="auravampiric"', 'set HZ4[113]="ancestralspirittarget"',
          "set HM4[114]='AZ10'", "set HN4[114]='AZ11'", "set HO4[114]='AZ12'", "set HP4[114]='AZ13'",
          'set HW4[114]="shockwave"', 'set HX4[114]="blizzard"', 'set HY4[114]="passive"', 'set HZ4[114]="breathoffire"']
    s = text.index(EOL + 'function V5 takes nothing returns nothing' + EOL)
    e = text.index(EOL + 'endfunction', s)
    if 'V' in PARTS: text = text[:e] + EOL + EOL.join(v5) + text[e:]

    # item builds: Monkey King uses Juggernaut's, Mars uses Axe's (BVE)
    bve = text.index(EOL + 'function BVE takes integer O5,unit it,boolean BUE returns nothing' + EOL)
    anchor = text.index(EOL + 'if BHE(O5)then', bve)
    if 'B' in PARTS: text = text[:anchor] + EOL + "if i1=='H0MK' then" + EOL + 'set i1=1315070563' + EOL + "elseif i1=='HMRS' then" + EOL + \
           'set i1=1332766568' + EOL + 'endif' + text[anchor:]
    # hero-role filter for AI picks (JR7)
    if 'R' in PARTS: sub_once(r'^(function JR7 takes integer JQ7,integer JS7 returns boolean)(?=\r?$)',
             r"\1" + EOL + "if JQ7=='H0MK' or JQ7=='HMRS' then" + EOL + 'return true' + EOL + 'endif', 'JR7')
    # random hero picks
    n_before = len(re.findall(r'GetRandomInt\((K04,K54|KL4,K14|XBE,XCE)\)', text))
    if 'P' in PARTS: text = re.sub(r'GetRandomInt\((K04,K54|KL4,K14|XBE,XCE)\)', r'PZRandHero(\1)', text)
    print('random hero picks hooked:', n_before)
    # normal economy for computer players: no XP handicap bonus, no extra starting/passive gold,
    # no dynamic (catch-up) gold/XP; health-aware retreat threshold
    if 'E' in PARTS:
        def insert_after_header(fname, header, lines_):
            global text
            h = EOL + header + EOL
            k = text.index(h) + len(h)
            # skip local declarations: JASS needs them first
            while text.startswith('local ', k):
                k = text.index(EOL, k) + len(EOL)
            text = text[:k] + EOL.join(lines_) + EOL + text[k:]
        # Q5F gives computers +25..+180% XP handicap depending on mode/difficulty (+60 more for Superpower)
        insert_after_header('Q5F', 'function Q5F takes player pl returns nothing',
                            ['set Y74[16+GetPlayerId(pl)]=R2I(GetPlayerHandicapXPBJ(pl))', 'return'])
        # Q2F: extra starting gold and the passive-gold bonus value i (paid every tick by QY8)
        q2 = text.index(EOL + 'function Q2F takes player pl,integer O5 returns nothing' + EOL)
        q2e = text.index(EOL + 'endfunction', q2)
        body = text[q2:q2e]
        for old, new in (('if((WT)or(O5==0))then', 'if(true)then'),
                         ('R2I(GetPlayerState(pl,PLAYER_STATE_RESOURCE_GOLD)*1.2)', 'GetPlayerState(pl,PLAYER_STATE_RESOURCE_GOLD)'),
                         ('set Y74[32+O27]=i', 'set i=0' + EOL + 'set Y74[32+O27]=i')):
            if body.count(old) != 1:
                sys.exit('Q2F patch: %r found %d times' % (old, body.count(old)))
            body = body.replace(old, new)
        text = text[:q2] + body + text[q2e:]
        # dynamic exp/gold (auto-enabled unless -ne/-ng): never start it
        insert_after_header('OZ9', 'function OZ9 takes nothing returns nothing', ['return'])
        insert_after_header('OA9', 'function OA9 takes nothing returns nothing', ['return'])
        # ME7 (should this hero retreat?): raise the HP threshold when outnumbered (PZThreat, computed by PZThreatTick)
        me = text.index(EOL + 'function ME7 takes unit it returns boolean' + EOL)
        mr = text.index(EOL + 'return((IsUnitType(it,UNIT_TYPE_HERO))and(R2I(GetWidgetLife(it))<(300+(GetHeroLevel(it)*30))*h/40.)', me)
        if mr - me > 400:
            sys.exit('ME7 layout changed')
        text = text[:mr] + EOL + 'set h=RMinBJ(h+PZThreat[p],70.)' + text[mr:]
        print('economy normalized, retreat patched')
    # inject globals and functions, start from main
    if 'G' in PARTS:
        gi = text.index(EOL + 'endglobals')
        text = text[:gi] + EOL + GLOB.replace('\n', EOL) + text[gi:]
        ge = text.index('endglobals' + EOL) + len('endglobals' + EOL)
        text = text[:ge] + FUNCS.replace('\n', EOL) + EOL + text[ge:]
        mi = text.index(EOL + 'function main takes nothing returns nothing')
        me = text.index(EOL + 'endfunction', mi)
        if 'I' not in PARTS:
            text = text[:me] + EOL + 'call ExecuteFunc("PZInit")' + text[me:]
    files[sname] = (b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8')
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    with open(os.path.splitext(OUT)[0] + '.j', 'w', encoding='utf-8', newline='') as f:
        f.write(text)

# ---------------- map name (header + wts)
FK = {n.lower(): n for n in files}
wts = files.get(FK.get('war3map.wts'))
w3i = files[FK['war3map.w3i']]
mm = re.search(rb'TRIGSTR_(\d+)', w3i[12:80])
if wts and mm:
    w = wts.decode('utf-8-sig')
    w2 = re.sub(r'(STRING %s\s*\{\s*)(.*?)(\s*\})' % mm.group(1).decode(), lambda x: x.group(1) + NAME + x.group(3), w, count=1, flags=re.S)
    files[FK['war3map.wts']] = (b'\xef\xbb\xbf' if wts.startswith(b'\xef\xbb\xbf') else b'') + w2.encode('utf-8')
head = bytearray(tm.raw[:tm.base])
end = head.index(0, 8)
rest = head[end + 1:end + 9]
newh = b'HM3W' + head[4:8] + NAME.encode('utf-8') + b'\0' + rest
newh += b'\0' * (tm.base - len(newh))

size = write_mpq(OUT, bytes(newh), [(n, files[n]) for n in order], sector_shift=3)
print('wrote %s (%.1f MB), test=%s, name=%s' % (OUT, size / 1e6, TEST, NAME))
