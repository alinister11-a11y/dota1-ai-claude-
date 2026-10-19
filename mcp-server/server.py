#!/usr/bin/env python3
"""wc3-dota: an MCP server that lets Claude play DotA (Warcraft III 1.27b) as your opponent.

It talks to the "DotA 6.88f AI vs Claude" map through two small files in
<Warcraft III>\\CustomMapData\\ClaudeBridge: the map writes state.txt every 0.5 s and reads
commands from cmd.txt (synced to every LAN client by the map). Standard library only; speaks
MCP over stdio (newline-delimited JSON-RPC 2.0).
"""
import difflib
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
WC3 = os.environ.get('WC3_DIR') or os.path.dirname(HERE)
BRIDGE = os.path.join(WC3, 'CustomMapData', 'ClaudeBridge')
STATE = os.path.join(BRIDGE, 'state.txt')
CMD = os.path.join(BRIDGE, 'cmd.txt')
KB_PATH = os.path.join(HERE, 'data', 'kb.json')
LOG_PATH = os.path.join(HERE, 'logs', 'server.log')
MAP_TITLE = 'DotA 6.88f AI vs Claude'
MAP_FILE = r'Maps\Scenario\DotA_6_88f_AI_vs_Claude.w3x'
VERSION = '1.0.0'
MAX_PAYLOAD = 210          # characters per synced command batch (map limit is ~228)
HEARTBEAT_LIMIT = 40.0     # the map rewrites state.txt at least every 15 s while a game runs


def log(*a):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a) + '\n')
    except OSError:
        pass


# ----------------------------------------------------------------------------- helpers
def raw2int(s):
    return int.from_bytes(s.encode('latin-1'), 'big')


def int2raw(i):
    try:
        s = (int(i) & 0xFFFFFFFF).to_bytes(4, 'big').decode('latin-1')
        return s if s.isprintable() else str(i)
    except (ValueError, OverflowError):
        return str(i)


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def num(s, default=0):
    try:
        return int(s)
    except (TypeError, ValueError):
        try:
            return int(float(s))
        except (TypeError, ValueError):
            return default


def fnum(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def team_of(pid):
    return 'Sentinel' if 0 <= pid <= 5 else 'Scourge' if 6 <= pid <= 11 else 'neutral'


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def encode(s):
    """4 printable-ASCII characters per integer, base 96 (char code - 31), as the map decodes it."""
    s = ''.join(ch if 32 <= ord(ch) <= 126 else '?' for ch in s)
    out = []
    for i in range(0, len(s), 4):
        v = 0
        for j, ch in enumerate(s[i:i + 4]):
            v += (ord(ch) - 31) * (96 ** j)
        out.append(v)
    return out


def best_match(query, names):
    """names: list of (display, key). Returns key of the best fuzzy match or None."""
    q = norm(query)
    if not q:
        return None
    exact = [k for d, k in names if norm(d) == q]
    if exact:
        return exact[0]
    pre = [k for d, k in names if norm(d).startswith(q)]
    if pre:
        return pre[0]
    sub = [k for d, k in names if q in norm(d)]
    if sub:
        return sub[0]
    keys = {norm(d): k for d, k in names}
    close = difflib.get_close_matches(q, list(keys), n=1, cutoff=0.6)
    return keys[close[0]] if close else None


# ----------------------------------------------------------------------------- knowledge
class KB:
    def __init__(self, path):
        d = json.load(open(path, encoding='utf-8'))
        self.heroes = {h['id']: h for h in d['heroes']}
        self.hero_by_int = {raw2int(h['id']): h for h in d['heroes']}
        self.items = {i['id']: i for i in d['items']}
        self.item_names = d.get('item_names', {})
        self.unit_names = d.get('unit_names', {})
        self.skill = {}
        for h in d['heroes']:
            for s in h['skills']:
                self.skill[raw2int(s['id'])] = s
        names = []
        for h in d['heroes']:
            names.append((h['name'], h['id']))
            if h.get('proper'):
                names.append((h['proper'], h['id']))
        self.hero_names = names
        self.item_match = [(i['name'], i['id']) for i in d['items']]

    def hero(self, type_int):
        return self.hero_by_int.get(type_int)

    def hero_label(self, type_int):
        h = self.hero(type_int)
        return h['name'] if h else int2raw(type_int)

    def unit_label(self, type_int):
        r = int2raw(type_int)
        h = self.hero(type_int)
        if h:
            return h['name']
        return self.unit_names.get(r) or self.item_names.get(r) or r

    def item_label(self, type_int):
        r = int2raw(type_int)
        return self.item_names.get(r) or (self.items.get(r) or {}).get('name') or r

    def find_hero(self, q):
        return best_match(q, self.hero_names)

    def find_item(self, q):
        return best_match(q, self.item_match)


# ----------------------------------------------------------------------------- game state
_STATE_CACHE = {'key': None, 'snap': None}


def read_state(retries=10):
    """Parse state.txt. Returns (snapshot dict, age seconds) or (None, None).
    The file is only opened when it changed, so polling does not get in the way of the game writing it."""
    for _ in range(retries):
        try:
            st = os.stat(STATE)
            key = (st.st_mtime_ns, st.st_size)
            if key == _STATE_CACHE['key']:
                return _STATE_CACHE['snap'], time.time() - st.st_mtime
            with open(STATE, encoding='utf-8', errors='replace') as f:
                txt = f.read()
        except FileNotFoundError:
            return None, None
        except OSError:
            time.sleep(0.05)
            continue
        lines = re.findall(r'call Preload\( "(.*)" \)\s*$', txt, re.M)
        if lines and lines[-1].startswith('Z|'):
            snap = parse_state(lines)
            _STATE_CACHE.update(key=key, snap=snap)
            return snap, time.time() - st.st_mtime
        time.sleep(0.06)
    return None, None


def parse_state(lines):
    s = {'heroes': [], 'units': [], 'buildings': [], 'events': [], 'pickable': [], 'abil': [], 'items': []}
    for ln in lines:
        try:
            parse_line(s, ln)
        except (IndexError, ValueError):
            log('bad state line', ln[:120])
    return s


def parse_line(s, ln):
    tag, _, rest = ln.partition('|')
    f = rest.split('|')
    if tag == 'S':                  # format 2: stable fields first, game time last
        keys = ['ver', 'nonce', 'cp', 'owner', 'solo', 'retreat', 'bld', 'linked', 'auto', 'has_hero', 'man',
                'seq', 'ok', 'err', 'req', 'hold_left', 't']
        if len(f) <= 7:             # no Claude slot: S|2|nonce|-1|owner|solo|req|t
            keys = ['ver', 'nonce', 'cp', 'owner', 'solo', 'req', 't']
        for k, v in zip(keys, f):
            s[k] = fnum(v) if k in ('t', 'hold_left', 'retreat') else num(v)
    elif tag == 'H':
        keys = ['type', 'maxhp', 'maxmp', 'str', 'agi', 'int', 'lvl', 'xp', 'pts', 'gold', 'alive', 'order',
                'dmgby', 'dmg', 'mp', 'hp', 'x', 'y']
        s['hero'] = {k: (v if k == 'order' else num(v)) for k, v in zip(keys, f)}
    elif tag == 'A':                # ability:level:game time of last cast (-1000 = never)
        for e in filter(None, rest.split(';')):
            a, lv, cast_t = (e.split(':') + ['0', '-1000'])[:3]
            s['abil'].append((num(a), num(lv), fnum(cast_t, -1000)))
    elif tag == 'C':
        s['counts'] = dict(zip(['allies', 'enemies', 'neutral'], (num(x) for x in f)))
    elif tag == 'W':
        s['wake'] = rest
    elif tag == 'I':
        for e in filter(None, rest.split(';')):
            t, c = (e.split(':') + ['0'])[:2]
            s['items'].append((num(t), num(c)))
    elif tag in ('E', 'F'):
        h = {'enemy': tag == 'E', 'pid': num(f[0]), 'name': f[1], 'type': num(f[2]), 'lvl': num(f[3]),
             'alive': f[4] == '1', 'vis': f[5] == '1'}
        if len(f) >= 12:
            h.update({'maxhp': num(f[6]), 'maxmp': num(f[7]), 'hp': num(f[8]), 'mp': num(f[9]),
                      'x': num(f[10]), 'y': num(f[11])})
        s['heroes'].append(h)
    elif tag in ('N', 'B'):
        for e in filter(None, rest.split(';')):
            p = e.split(':')
            if len(p) >= 7:
                u = {'ref': p[0], 'type': num(p[1]), 'rel': p[2], 'maxhp': num(p[3]), 'hp': num(p[4]),
                     'x': num(p[5]), 'y': num(p[6])}
                (s['units'] if tag == 'N' else s['buildings']).append(u)
    elif tag == 'P':
        s['pickable'] += [num(x) for x in rest.split(';') if x]
    elif tag == 'V':
        p = rest.split('|', 2)
        if len(p) == 3:
            s['events'].append((num(p[0]), fnum(p[1]), p[2]))


class Game:
    def __init__(self):
        self.kb = KB(KB_PATH)
        self.seq = int(time.time()) % 1000000000
        self.req = int(time.time() * 7) % 1000000000
        self.last_cmd = None
        self.nonce = None
        self.last_event = -1
        self.buildings = []
        self.buildings_t = -1
        self.tracked_for = None
        self.last_send = 0.0
        self.snap = None

    # -- low level
    # The map writes state.txt only when asked (each write costs the game a ~50 ms hitch), after commands
    # ran, when a watch fires, and as a 15 s heartbeat. So: reuse a recent snapshot when that is good
    # enough, and ask for a fresh one only when needed.
    def state(self):
        s, age = read_state()
        if s is None:
            return None, None
        if s['buildings']:
            self.buildings, self.buildings_t = s['buildings'], s.get('t', 0)
        self.snap = s
        return s, age

    def live(self, max_age=0.0):
        """A snapshot no older than max_age seconds (0 = ask the map for a fresh one)."""
        s, age = self.state()
        if s is None:
            raise GameError('No bridge state found. Start the "%s" map (see game_status).' % MAP_TITLE)
        if age > HEARTBEAT_LIMIT:
            raise GameError('The bridge state is %.0f s old: the game is not running, is paused, or has ended. '
                            'Call game_status for setup help.' % age)
        if age <= max_age:
            return s
        req = self.write_cmd(None)
        return self.await_state(lambda x: x.get('req') == req, 4.0)

    def await_state(self, cond, timeout):
        end = time.time() + timeout
        while time.time() < end:
            time.sleep(0.2)
            s, _ = self.state()
            if s is not None and cond(s):
                return s
        raise GameError('The map did not answer within %.0f s: the game may be paused, lagging or over.' % timeout)

    def write_cmd(self, payload, nonce=0, watch=0.0, mask=63):
        """Write cmd.txt. payload None keeps the last command (the map ignores a seq it has run) and only
        bumps the request id, which makes the map write state.txt; watch > 0 asks it to wait for an event."""
        if payload is not None:
            self.seq += 1
            self.last_cmd = (self.seq, nonce, encode(payload))
        self.req += 1
        seq, nn, ints = self.last_cmd or (0, 0, [])
        tokens = [str(seq), str(nn), str(len(ints))] + [str(v) for v in ints] + [
            str(self.req), str(int(watch * 10)), str(mask)]
        lines, cur = [], ''
        for tok in tokens:
            if cur and len(cur) + 1 + len(tok) > 230:
                lines.append(cur)
                cur = tok
            else:
                cur = tok if not cur else cur + ' ' + tok
        lines.append(cur)
        if len(lines) > 3 or len(tokens) > 60:
            raise GameError('command batch too long')
        # Only non-empty string literals: WC3's preload-file parser crashes (Storm.dll stack overrun) on "".
        # The map clears the three names before reading, so missing lines read back as empty.
        body = 'function PreloadFiles takes nothing returns nothing\r\n\r\n'
        for i, ln in enumerate(lines):
            body += '\tcall SetPlayerName(Player(%d), "%s")\r\n' % (13 + i, ln)
        body += '\r\nendfunction\r\n'
        os.makedirs(BRIDGE, exist_ok=True)
        tmp = CMD + '.tmp'
        with open(tmp, 'w', encoding='ascii', newline='') as f:
            f.write(body)
        for _ in range(40):
            try:
                os.replace(tmp, CMD)
                break
            except PermissionError:
                time.sleep(0.03)
        else:
            raise GameError('could not write the command file (locked)')
        if payload is not None:
            self.last_send = time.time()
            log('send', self.seq, payload)
        return self.req

    def send(self, payload, timeout=5.0):
        """Send one batch (';'-separated map commands); returns (results, fresh snapshot)."""
        s = self.live(max_age=HEARTBEAT_LIMIT)
        self.write_cmd(payload, s['nonce'])
        seq = self.seq
        tag = 'res %d ' % seq
        try:
            s2 = self.await_state(lambda x: x.get('seq') == seq and any(e[2].startswith(tag) for e in x['events'])
                                  or x.get('nonce') != s['nonce'], timeout)
        except GameError:
            return ['(no answer from the map within %.0f s - the game may be paused or lagging)' % timeout], None
        if s2.get('nonce') != s['nonce']:
            raise GameError('a new game started while sending')
        return [e[2][len(tag):] for e in s2['events'] if e[2].startswith(tag)], s2

    def send_all(self, cmds, timeout=5.0):
        out, batch, snap = [], '', None
        for c in cmds:
            if batch and len(batch) + 1 + len(c) > MAX_PAYLOAD:
                r, snap = self.send(batch, timeout)
                out += r
                batch = ''
            batch = c if not batch else batch + ';' + c
        if batch:
            r, snap = self.send(batch, timeout)
            out += r
        return out, snap

    def watch(self, seconds, mask=63):
        """Let the map wake us when something happens; one state write instead of polling."""
        s = self.live(max_age=HEARTBEAT_LIMIT)
        req = self.write_cmd(None, watch=seconds, mask=mask)
        return self.await_state(lambda x: x.get('req') == req and x.get('wake'), seconds + 4.0)

    def ensure(self, max_age=0.0):
        """Handshake with a new game and keep the map's skill tracking in sync with our hero."""
        s = self.live(max_age)
        msgs = []
        if s.get('cp', -1) < 0:
            return s, msgs
        if self.nonce != s['nonce'] or not s.get('linked'):
            self.nonce = s['nonce']
            self.tracked_for = None
            self.last_event = -1
            self.buildings = []
            r, s2 = self.send('hello')
            msgs += r
            s = s2 or self.live()
        elif time.time() - self.last_send > 60:
            _, s2 = self.send('ping')                 # keeps the map from handing the hero back to its AI
            s = s2 or s
        h = s.get('hero')
        if h and self.tracked_for != h['type']:
            kh = self.kb.hero(h['type'])
            if kh:
                ids = [raw2int(x['id']) for x in kh['skills']][:8]
                cmds = []
                if [a for a, _, _ in s['abil']] != ids:       # the map keeps tracking across server restarts
                    cmds.append('trk ' + ' '.join(str(i) for i in ids))
                if not s.get('bld'):
                    cmds.append('build ' + ' '.join(str(kh['skills'].index(x)) for x in default_build(kh)))
                if cmds:
                    _, s2 = self.send_all(cmds)
                    s = s2 or self.live()
                self.tracked_for = h['type']
        return s, msgs

    # -- naming helpers
    def me_pid(self, s):
        return s.get('cp', -1)

    def hero_of(self, s, pid):
        for h in s['heroes']:
            if h['pid'] == pid:
                return h
        return None

    def my_skills(self, s):
        h = s.get('hero')
        kh = self.kb.hero(h['type']) if h else None
        return kh['skills'] if kh else []

    def resolve_target(self, s, tok):
        """-> (map_ref, x, y) for a target token: h<pid>/P<pid>, u<id>, me, hero or player name."""
        t = tok.strip().rstrip(',')
        lo = t.lower()
        if lo in ('me', 'self', 'myself'):
            h = s.get('hero') or {}
            return 'h%d' % s['cp'], h.get('x', 0), h.get('y', 0)
        m = re.fullmatch(r'[hp](\d{1,2})', lo)
        if m:
            pid = int(m.group(1))
            h = self.hero_of(s, pid)
            if pid == s['cp']:
                me = s.get('hero') or {}
                return 'h%d' % pid, me.get('x', 0), me.get('y', 0)
            if not h:
                raise GameError('player %d has no hero' % pid)
            if h['enemy'] and not h['vis']:
                raise GameError('%s is not visible right now' % self.kb.hero_label(h['type']))
            return 'h%d' % pid, h.get('x', 0), h.get('y', 0)
        m = re.fullmatch(r'u(\d+)', lo)
        if m:
            for u in s['units'] + self.buildings:
                if u['ref'] == lo:
                    return lo, u['x'], u['y']
            return lo, None, None
        cands = []
        for h in s['heroes']:
            if h['enemy'] and not h['vis']:
                continue
            cands.append((self.kb.hero_label(h['type']), h['pid']))
            cands.append((h['name'], h['pid']))
            kh = self.kb.hero(h['type'])
            if kh and kh.get('proper'):
                cands.append((kh['proper'], h['pid']))
        pid = best_match(t, cands)
        if pid is not None:
            h = self.hero_of(s, pid)
            return 'h%d' % pid, h.get('x', 0), h.get('y', 0)
        raise GameError('unknown or invisible target "%s" (use h<player>, u<id>, me, or a visible hero name)' % tok)

    def skill_status(self, s, sk):
        """-> (level, cooldown seconds left, mana cost at that level) from the tracked ability data."""
        levels = {a: (lv, cast_t) for a, lv, cast_t in s['abil']}
        lv, cast_t = levels.get(raw2int(sk['id']), (0, -1000))
        if not lv:
            return 0, 0.0, None
        cds = [c for c in (sk['cooldown'] or []) if c is not None]
        manas = [c for c in (sk['mana'] or []) if c is not None]
        cd = cds[min(lv, len(cds)) - 1] if cds else 0
        mana = manas[min(lv, len(manas)) - 1] if manas else None
        left = max(0.0, (cd or 0) - (s.get('t', 0) - cast_t)) if cast_t > -500 else 0.0
        return lv, left, mana

    def find_skill(self, s, q):
        skills = self.my_skills(s)
        if not skills:
            raise GameError('no hero yet')
        q = q.strip()
        active = [x for x in skills if x['base'] != 'Aamk']
        if re.fullmatch(r'[1-5]', q):
            i = int(q) - 1
            if i < len(active):
                return active[i]
        if len(q) == 1:
            for x in skills:
                if x['hotkey'].upper() == q.upper():
                    return x
        if norm(q) in ('stats', 'attribute', 'attributes', 'attributebonus'):
            for x in skills:
                if x['base'] == 'Aamk':
                    return x
        k = best_match(q, [(x['name'], i) for i, x in enumerate(skills)])
        if k is None:
            raise GameError('your hero has no skill like "%s". Skills: %s' % (q, ', '.join(x['name'] for x in skills)))
        return skills[k]

    # -- map geometry
    def lane_point(self, s, lane):
        """Where the creep waves meet in a lane: halfway between both teams' outermost towers."""
        mine = 's' if team_of(s['cp']) == 'Sentinel' else 'c'
        def lane_of(b):
            d = b['y'] - b['x']
            return 'mid' if abs(d) < 2500 else 'top' if d > 0 else 'bot'
        towers = [b for b in self.buildings if 'tower' in self.kb.unit_label(b['type']).lower()]
        own = [b for b in towers if b['rel'] == mine and lane_of(b) == lane]
        foe = [b for b in towers if b['rel'] != mine and lane_of(b) == lane]
        if not own or not foe:
            fallback = {'top': (-6200, 6000), 'mid': (0, 0), 'bot': (6200, -6400)}
            return fallback[lane]
        own_base = (-6800, -6800) if mine == 's' else (6600, 6200)
        o = max(own, key=lambda b: dist(b['x'], b['y'], *own_base))
        e = min(foe, key=lambda b: dist(b['x'], b['y'], *own_base))
        return int((o['x'] + e['x']) / 2), int((o['y'] + e['y']) / 2)

    # -- formatting
    def describe(self, s, events=True, full=False):
        kb = self.kb
        out = []
        cp = s.get('cp', -1)
        if cp < 0:
            return ('In game (t=%.0fs) but there is no computer slot for Claude. Host again and set one slot on the '
                    'other team to Computer.' % s.get('t', 0))
        mode = 'AUTOPILOT' if s.get('auto') else 'MANUAL'
        ctl = 'Claude steering' if s.get('man') else 'map AI steering'
        hold = ' (override %.0fs left)' % s['hold_left'] if s.get('auto') and s.get('hold_left', 0) > 0 else ''
        out.append('t=%.0fs | Claude = P%d (%s) | mode %s, %s%s | auto-retreat <%d%% | cmds ok %d / failed %d' % (
            s.get('t', 0), cp, team_of(cp), mode, ctl, hold, s.get('retreat', 20), s.get('ok', 0), s.get('err', 0)))
        h = s.get('hero')
        mx = my = 0
        if not h:
            out.append('No hero yet: pick one with pick_hero (%d heroes available to you).' % len(s['pickable']))
        else:
            mx, my = h['x'], h['y']
            kh = kb.hero(h['type'])
            pct = 100 * h['hp'] // max(1, h['maxhp'])
            status = 'ALIVE' if h['alive'] else 'DEAD (respawning)'
            out.append('ME: %s Lv%d %s HP %d/%d (%d%%) MP %d/%d at (%d,%d) gold %d skill-points %d order=%s%s' % (
                kb.hero_label(h['type']), h['lvl'], status, h['hp'], h['maxhp'], pct, h['mp'], h['maxmp'],
                mx, my, h['gold'], h['pts'], h['order'] or 'idle',
                ' | took %d dmg in last 0.5s from P%d' % (h['dmg'], h['dmgby']) if h['dmg'] > 0 else ''))
            if kh:
                parts = []
                for sk in kh['skills']:
                    lv, left, mana = self.skill_status(s, sk)
                    if sk['base'] == 'Aamk':
                        if lv:
                            parts.append('Stats L%d' % lv)
                        continue
                    tag = '%s[%s] L%d' % (sk['name'], sk['hotkey'] or '-', lv)
                    if not sk['order']:
                        tag += ' passive'
                    elif lv:
                        tag += ' %s%s' % ('READY' if left <= 0 else 'cd %.0fs' % left, ', %dmp' % mana if mana else '')
                    if sk['order'] and sk.get('cast'):
                        tag += ' (%s)' % sk['cast']
                    parts.append(tag)
                out.append('  skills: ' + ' | '.join(parts))
            inv = ['%d:%s%s' % (i + 1, kb.item_label(t), '(%d)' % c if c > 1 else '') for i, (t, c) in enumerate(s['items']) if t]
            out.append('  items: ' + (', '.join(inv) if inv else 'none'))
        enemies, allies = [], []
        for e in s['heroes']:
            name = '%s P%d %s Lv%d' % (kb.hero_label(e['type']), e['pid'], e['name'], e['lvl'])
            if not e['alive']:
                name += ' DEAD'
            elif e['vis'] or not e['enemy']:
                d = dist(mx, my, e['x'], e['y']) if h else 0
                name += ' HP %d/%d MP %d/%d at (%d,%d)%s' % (e['hp'], e['maxhp'], e['mp'], e['maxmp'], e['x'], e['y'],
                                                            ' dist %d' % d if h else '')
            else:
                name += ' (not visible)'
            (enemies if e['enemy'] else allies).append(name)
        out.append('ENEMY heroes: ' + ('; '.join(enemies) if enemies else 'none'))
        out.append('ALLY heroes: ' + ('; '.join(allies) if allies else 'none'))
        if h:
            near = sorted(s['units'], key=lambda u: dist(mx, my, u['x'], u['y']))
            groups = {}
            for u in near:
                groups.setdefault(u['rel'], []).append(u)
            labels = {'e': 'enemy units', 'a': 'allied units', 'n': 'neutral creeps', 'eb': 'ENEMY BUILDINGS',
                      'ab': 'allied buildings', 'nb': 'neutral buildings'}
            for rel in ('eb', 'e', 'n', 'a', 'ab'):
                us = groups.get(rel, [])
                if not us:
                    continue
                shown = us if full else us[:6]
                txt = ', '.join('%s %s %d/%d d%d' % (u['ref'], kb.unit_label(u['type']), u['hp'], u['maxhp'],
                                                     dist(mx, my, u['x'], u['y'])) for u in shown)
                more = ' (+%d more)' % (len(us) - len(shown)) if len(us) > len(shown) else ''
                out.append('  near %s (%d): %s%s' % (labels[rel], len(us), txt, more))
            if s.get('counts'):
                out.append('  allied units nearby: %d' % s['counts']['allies'])
        if events:
            new = [e for e in s['events'] if e[0] > self.last_event]
            if new:
                self.last_event = max(e[0] for e in new)
                lines = [self.event_text(s, e) for e in new]
                lines = [x for x in lines if x]
                if lines:
                    out.append('EVENTS: ' + ' | '.join(lines))
        return '\n'.join(out)

    def player_label(self, s, pid):
        if pid == s.get('cp'):
            return 'Claude(P%d)' % pid
        h = self.hero_of(s, pid)
        if h:
            return '%s(P%d %s)' % (h['name'], pid, self.kb.hero_label(h['type']))
        return 'P%d' % pid if pid >= 0 else 'someone'

    def event_text(self, s, e):
        _, t, txt = e
        w = txt.split(' ', 2)
        k = w[0]
        try:
            if k == 'kill':
                return '[%.0fs] %s killed %s' % (t, self.player_label(s, int(w[1])), self.player_label(s, int(w[2])))
            if k == 'chat':
                return '[%.0fs] CHAT %s: "%s"' % (t, self.player_label(s, int(w[1])), w[2] if len(w) > 2 else '')
            if k == 'building':
                p = txt.split()
                return '[%.0fs] %s destroyed (%s)' % (t, self.kb.unit_label(int(p[2])), team_of(int(p[1])))
            if k == 'level':
                return '[%.0fs] I reached level %s' % (t, w[1])
            if k == 'learned':
                sk = self.kb.skill.get(int(w[1]))
                return '[%.0fs] learned %s' % (t, sk['name'] if sk else w[1])
            if k in ('item+', 'item-'):
                return '[%.0fs] %s %s' % (t, 'got' if k == 'item+' else 'lost', self.kb.item_label(int(w[1])))
            if k == 'cast':
                sk = self.kb.skill.get(int(w[1]))
                return '[%.0fs] cast %s' % (t, sk['name'] if sk else self.kb.unit_label(int(w[1])))
            if k == 'hero':
                return '[%.0fs] my hero is %s' % (t, self.kb.hero_label(int(w[1])))
            if k in ('res', 'slot'):
                return None
        except (ValueError, IndexError):
            pass
        return '[%.0fs] %s' % (t, txt)


class GameError(Exception):
    pass


def default_build(kh):
    """Skill learn order used until Claude sets its own: max the first skill, ultimate at 6/11/16, then stats.
    The map skips entries that cannot be learned yet and comes back to them."""
    skills = kh['skills']
    stats = next((x for x in skills if x['base'] == 'Aamk'), None)
    act = [x for x in skills if x['base'] != 'Aamk']
    if len(act) < 4:
        return act * 4 + ([stats] * 10 if stats else [])
    ult = next((x for x in act if x['levels'] == 3), act[3])
    a, b, c = [x for x in act if x is not ult][:3]
    order = [a, b, a, c, a, ult, a, b, b, b, ult, c, c, c, ult]
    if stats:
        order += [stats] * 10
    return order[:25]


# ----------------------------------------------------------------------------- tools
GAME = None


def game():
    global GAME
    if GAME is None:
        GAME = Game()
    return GAME


def war3_running():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq war3.exe', '/NH'], capture_output=True, text=True,
                             timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
        return 'war3.exe' in out.lower()
    except Exception:
        return None


def local_files_enabled():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Blizzard Entertainment\Warcraft III')
        v, _ = winreg.QueryValueEx(k, 'Allow Local Files')
        return v == 1
    except Exception:
        return False


SETUP = """How to start a game against Claude:
1. Warcraft III > Local Area Network > Create Game, pick the map "%s" (Maps\\Scenario).
2. Take a slot yourself (you must be the first human slot in the list - normally the host).
3. Set one slot on the OTHER team to "Computer": the first computer on the enemy team is Claude.
   Other slots can be friends or normal computers.
4. Start, type a game mode as usual (e.g. -ap, -sd, -apso). Claude has 75 s of game time to pick a hero,
   otherwise the map's AI picks one for that slot.""" % MAP_TITLE


def tool_game_status(args):
    g = game()
    lines = []
    running = war3_running()
    lines.append('Warcraft III running: %s' % {True: 'yes', False: 'no', None: 'unknown'}[running])
    if not local_files_enabled():
        lines.append('PROBLEM: registry value HKCU\\Software\\Blizzard Entertainment\\Warcraft III\\"Allow Local Files" '
                     'is not 1, so the map cannot read Claude\'s commands. Set it to 1 and restart Warcraft III.')
    if not os.path.exists(os.path.join(WC3, MAP_FILE)):
        lines.append('PROBLEM: map file missing: %s' % os.path.join(WC3, MAP_FILE))
    s, age = g.state()
    if s is None or age > HEARTBEAT_LIMIT:
        lines.append('No live game (bridge state %s).' % ('missing' if s is None else '%.0f s old' % age))
        lines.append(SETUP)
        return '\n'.join(lines)
    try:
        s, _ = g.ensure()
    except GameError as e:
        lines.append('Bridge error: %s' % e)
    if s.get('cp', -1) < 0:
        lines.append('In game, but no Computer slot for Claude was found.')
        lines.append(SETUP)
        return '\n'.join(lines)
    lines.append('Live game, linked=%s. Bridge owner (human whose PC runs this) = P%d.' % (bool(s.get('linked')), s['owner']))
    lines.append(g.describe(s))
    if not s.get('hero'):
        lines.append('Next: list_heroes, then pick_hero.')
    return '\n'.join(lines)


def tool_list_heroes(args):
    g = game()
    flt = norm(args.get('filter', ''))
    s = None
    try:
        s = g.live(max_age=HEARTBEAT_LIMIT)
    except GameError:
        pass
    avail = set(s['pickable']) if s and not s.get('hero') else None
    rows = []
    for h in sorted(g.kb.heroes.values(), key=lambda x: x['name']):
        hid = raw2int(h['id'])
        if avail is not None and hid not in avail:
            continue
        text = '%s / %s [%s]: %s' % (h['name'], h['proper'], h['primary'] or '?',
                                     ', '.join(x['name'] for x in h['skills'] if x['base'] != 'Aamk'))
        if flt and flt not in norm(text):
            continue
        rows.append(text)
    head = ('%d heroes you can pick now' % len(rows)) if avail is not None else ('%d heroes (not in a pick phase)' % len(rows))
    return head + ':\n' + '\n'.join(rows)


def tool_pick_hero(args):
    g = game()
    s, _ = g.ensure(max_age=3)
    if s.get('cp', -1) < 0:
        raise GameError('no Claude slot in this game')
    if s.get('hero'):
        raise GameError('already playing %s' % g.kb.hero_label(s['hero']['type']))
    hid = g.kb.find_hero(args.get('hero', ''))
    if not hid:
        raise GameError('no hero matches "%s"' % args.get('hero'))
    h = g.kb.heroes[hid]
    if s['pickable'] and raw2int(hid) not in s['pickable']:
        raise GameError('%s is not available to you now (taken or not offered in this mode). Use list_heroes.' % h['name'])
    cmds = ['pick %d' % raw2int(hid)]
    if args.get('say'):
        cmds.append('say ' + args['say'].replace(';', ','))
    res, _ = g.send_all(cmds)
    s, _ = g.ensure(max_age=5)
    out = 'pick %s: %s' % (h['name'], '; '.join(res))
    if s.get('hero'):
        out += '\n' + tool_lookup({'query': h['name']}) + '\n\n' + g.describe(s)
    return out


def tool_get_state(args):
    g = game()
    s, _ = g.ensure()
    return g.describe(s, full=bool(args.get('full')))


def tool_wait(args):
    """Block until something worth reacting to happens, then return the state."""
    g = game()
    secs = max(0.5, min(30.0, float(args.get('seconds', 5))))
    g.ensure(max_age=HEARTBEAT_LIMIT)
    s = g.watch(secs)                       # the map checks the wake conditions itself and writes once
    s, _ = g.ensure(max_age=5)
    return 'woke: %s\n%s' % (s.get('wake') or 'timeout', g.describe(s))


ACT_HELP = """Commands (separate with ';' or new lines):
  move X Y | move <target>        walk (no fighting)
  amove X Y                       attack-move (fight whatever is met)
  attack <target>                 attack a unit/hero
  cast <skill> [<target> | X Y]   skill by name, hotkey letter or number 1-4
  learn <skill> | build <s1>, <s2>, ...   learn now / set a learn order used automatically
  buy <item>                      buy from a shop within ~1000 range (hero must be at the shop)
  use <slot 1-6 | item> [<target> | X Y]
  stop | hold | back (walk to fountain) | lane top|mid|bot (attack-move to where the waves meet)
  say <text>                      all-chat message to the players
  mode auto | mode manual         auto: map AI plays between your orders; manual: you control everything
  holdtime <sec>                  in auto mode, how long the AI stays off after each order (default 8)
  retreat_at <pct>                while you steer, walk home automatically below this HP% (default 20, 0 = off)
Targets: h<player#> (hero of that player, e.g. h1), u<id> (from get_state), me, or a visible hero name."""


def tool_act(args):
    g = game()
    s, _ = g.ensure(max_age=3)
    text = args.get('commands', '')
    cmds = []
    notes = []
    for raw in re.split(r'[;\n]', text):
        c = raw.strip()
        if not c:
            continue
        op, _, rest = c.partition(' ')
        op = op.lower()
        rest = rest.strip()
        try:
            cmds.append(translate(g, s, op, rest))
        except GameError as e:
            notes.append('"%s": %s' % (c, e))
    res, snap = g.send_all(cmds) if cmds else ([], None)
    s2, _ = g.ensure(max_age=5) if snap else g.ensure(max_age=3)
    out = []
    if notes:
        out.append('Not sent: ' + ' | '.join(notes))
    if res:
        out.append('Results: ' + ' | '.join(res))
    out.append(g.describe(s2))
    return '\n'.join(out)


def coords(rest):
    m = re.fullmatch(r'\(?\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*\)?', rest.strip())
    return (int(float(m.group(1))), int(float(m.group(2)))) if m else None


def translate(g, s, op, rest):
    kb = g.kb
    if op in ('say', 'chat', 'all'):
        return 'say ' + rest.replace(';', ',')[:120]
    if op == 'mode':
        return 'mode ' + ('auto' if rest.lower().startswith('a') else 'man')
    if op in ('holdtime', 'hold_time', 'override'):
        return 'hold %d' % num(rest, 8)
    if op in ('retreat_at', 'retreatat', 'autoretreat'):
        return 'rt %d' % num(rest.rstrip('%'), 20)
    if op in ('stop', 's'):
        return 'st'
    if op in ('hold', 'holdposition'):
        return 'hp'
    if op in ('back', 'retreat', 'home', 'fountain'):
        return 'bk'
    if op in ('move', 'mv', 'go', 'amove', 'attackmove', 'am'):
        xy = coords(rest)
        if not xy:
            _, x, y = g.resolve_target(s, rest)
            if x is None:
                raise GameError('unknown position of %s' % rest)
            xy = (x, y)
        return ('am' if op in ('amove', 'attackmove', 'am') else 'mv') + ' %d %d' % xy
    if op == 'lane':
        lane = rest.lower()[:3]
        if lane not in ('top', 'mid', 'bot'):
            raise GameError('lane must be top, mid or bot')
        return 'am %d %d' % g.lane_point(s, lane)
    if op in ('attack', 'at', 'a', 'kill', 'hit'):
        ref, _, _ = g.resolve_target(s, rest)
        return 'at ' + ref
    if op in ('cast', 'c', 'skill'):
        if not rest:
            raise GameError('cast what?')
        m = re.fullmatch(r'(.+?)\s+\(?(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\)?', rest)
        tgt, point = '', None
        if m:
            sk = g.find_skill(s, m.group(1))
            point = (int(float(m.group(2))), int(float(m.group(3))))
        else:
            # shortest prefix naming one of my skills whose remainder is a valid target (or nothing)
            parts, sk, err = rest.split(), None, None
            for n in range(1, len(parts) + 1):
                try:
                    cand = g.find_skill(s, ' '.join(parts[:n]))
                except GameError as e:
                    err = err or e
                    continue
                rem = ' '.join(parts[n:])
                if rem:
                    try:
                        g.resolve_target(s, rem)
                    except GameError as e:
                        err = e
                        continue
                sk, tgt = cand, rem
                break
            if sk is None:
                raise err or GameError('cannot parse "%s"' % rest)
        if not sk['order']:
            raise GameError('%s is passive' % sk['name'])
        lv, left, mana = g.skill_status(s, sk)
        h = s.get('hero') or {}
        if not lv:
            raise GameError('%s is not learned yet' % sk['name'])
        if left > 0.5:
            raise GameError('%s is on cooldown (%.0fs left)' % (sk['name'], left))
        if mana and h.get('mp', 0) < mana:
            raise GameError('not enough mana for %s (%d/%d)' % (sk['name'], h.get('mp', 0), mana))
        base = 'cs %d %s' % (raw2int(sk['id']), sk['order'])
        if point:
            return base + ' %d %d' % point
        if not tgt:
            return base
        ref, x, y = g.resolve_target(s, tgt)
        if sk.get('cast') == 'point' and x is not None:
            return base + ' %d %d' % (x, y)
        return base + ' ' + ref
    if op in ('learn', 'lr', 'level'):
        return 'lr %d' % raw2int(g.find_skill(s, rest)['id'])
    if op == 'build':                         # sent as indexes into the hero's skill list (tracked by the map)
        skills = g.my_skills(s)
        idx = [str(skills.index(g.find_skill(s, x))) for x in re.split(r'[,>]', rest) if x.strip()]
        return 'build ' + ' '.join(idx[:25])
    if op in ('buy', 'purchase'):
        iid = kb.find_item(rest)
        if not iid:
            raise GameError('no shop item like "%s"' % rest)
        it = kb.items[iid]
        if not it['buyable']:
            raise GameError('%s is not sold directly: buy its parts (%s)' % (it['name'], ', '.join(it['requires']) or '?'))
        return 'by %d' % raw2int(iid)
    if op in ('use', 'item'):
        parts = rest.split(None, 1)
        if not parts:
            raise GameError('use which slot?')
        if re.fullmatch(r'[1-6]', parts[0]):
            slot = int(parts[0])
            tgt = parts[1] if len(parts) > 1 else ''
        else:
            inv = [(kb.item_label(t), i + 1) for i, (t, c) in enumerate(s['items']) if t]
            slot = best_match(parts[0], inv)
            tgt = parts[1] if len(parts) > 1 else ''
            if slot is None:
                raise GameError('no inventory item like "%s"' % parts[0])
        if not tgt:
            return 'us %d' % slot
        xy = coords(tgt)
        if xy:
            return 'us %d %d %d' % (slot, xy[0], xy[1])
        ref, _, _ = g.resolve_target(s, tgt)
        return 'us %d %s' % (slot, ref)
    if op == 'pick':
        hid = kb.find_hero(rest)
        if not hid:
            raise GameError('no hero like "%s"' % rest)
        return 'pick %d' % raw2int(hid)
    raise GameError('unknown command "%s"' % op)


def tool_lookup(args):
    g = game()
    q = args.get('query', '')
    hid = g.kb.find_hero(q)
    iid = g.kb.find_item(q)
    nq = norm(q)
    h = g.kb.heroes.get(hid) if hid else None
    it = g.kb.items.get(iid) if iid else None
    # prefer whichever name matches more closely
    if h and it:
        hs = max(difflib.SequenceMatcher(None, nq, norm(h['name'])).ratio(), difflib.SequenceMatcher(None, nq, norm(h['proper'])).ratio())
        if difflib.SequenceMatcher(None, nq, norm(it['name'])).ratio() > hs:
            h = None
        else:
            it = None
    if h:
        out = ['%s / %s [%s] STR %s(+%s) AGI %s(+%s) INT %s(+%s)' % (
            h['name'], h['proper'], h['primary'], h['str'], h['str+'], h['agi'], h['agi+'], h['int'], h['int+'])]
        for sk in h['skills']:
            if sk['base'] == 'Aamk':
                continue
            out.append('- %s [%s] %s | cd %s | mana %s | range %s\n  %s' % (
                sk['name'], sk['hotkey'] or '-', 'order=' + sk['order'] if sk['order'] else 'passive',
                sk['cooldown'], sk['mana'], sk['range'], sk['desc'][:220]))
        return '\n'.join(out)
    if it:
        return '%s: %d gold%s at %s\n%s%s' % (
            it['name'], it['cost'], '' if it['buyable'] else ' (combined item - not sold directly)',
            ', '.join(it['shop_names']), it['desc'][:260],
            ('\nRequires: ' + ', '.join(it['requires'])) if it['requires'] else '')
    return 'nothing found for "%s"' % q


TOOLS = [
    {'name': 'game_status',
     'description': 'Check whether a Warcraft III DotA game against Claude is running and linked, and get setup '
                    'instructions if not. Call this first.',
     'inputSchema': {'type': 'object', 'properties': {}}, 'fn': tool_game_status},
    {'name': 'list_heroes',
     'description': 'List heroes. During the pick phase only the heroes Claude may pick now are listed.',
     'inputSchema': {'type': 'object', 'properties': {
         'filter': {'type': 'string', 'description': 'optional text filter, e.g. "STR" or "stun"'}}},
     'fn': tool_list_heroes},
    {'name': 'pick_hero',
     'description': 'Pick Claude\'s hero by name (e.g. "Rogue Knight" or "Sven").',
     'inputSchema': {'type': 'object', 'properties': {
         'hero': {'type': 'string'},
         'say': {'type': 'string', 'description': 'optional all-chat message to send with the pick'}},
         'required': ['hero']}, 'fn': tool_pick_hero},
    {'name': 'get_state',
     'description': 'Current game state from Claude\'s point of view: own hero, skills with cooldowns, items, '
                    'visible heroes, nearby units with ids, and new events (kills, chat, level ups).',
     'inputSchema': {'type': 'object', 'properties': {
         'full': {'type': 'boolean', 'description': 'list every nearby unit instead of the closest few'}}},
     'fn': tool_get_state},
    {'name': 'wait',
     'description': 'Wait up to N seconds (max 30) and return early when something happens: an enemy hero '
                    'appears, Claude takes damage or drops below 40% HP, dies/respawns, gets a skill point, '
                    'or a kill/chat/building event. Returns the state.',
     'inputSchema': {'type': 'object', 'properties': {'seconds': {'type': 'number'}}}, 'fn': tool_wait},
    {'name': 'act',
     'description': 'Send orders to Claude\'s hero (one call can hold several). ' + ACT_HELP,
     'inputSchema': {'type': 'object', 'properties': {'commands': {'type': 'string'}}, 'required': ['commands']},
     'fn': tool_act},
    {'name': 'lookup',
     'description': 'Look up a hero (skills, cooldowns, mana) or a shop item (price, shop, recipe).',
     'inputSchema': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']},
     'fn': tool_lookup},
]

INSTRUCTIONS = """You are playing DotA (Warcraft III) live against the user, as the enemy team's hero.
Flow: game_status -> (wait for the user to start the game) -> list_heroes -> pick_hero -> play.
Playing: keep a tight loop of wait/get_state -> act until the game ends; keep each step short because the
game runs in real time. In 'auto' mode the map's AI handles laning between your orders and each order gives
you control for 'holdtime' seconds; use 'mode manual' only when you want full control. Use skills on enemy
heroes when they are in range, retreat ('back') when low on HP, buy items at the fountain shops, learn
skills when you have points (or set 'build' once). Answer chat with 'say'. Be a fair, fun opponent."""


# ----------------------------------------------------------------------------- MCP plumbing
def reply(mid, result=None, error=None):
    msg = {'jsonrpc': '2.0', 'id': mid}
    if error is not None:
        msg['error'] = error
    else:
        msg['result'] = result
    sys.stdout.write(json.dumps(msg) + '\n')
    sys.stdout.flush()


def handle(msg):
    method = msg.get('method')
    mid = msg.get('id')
    params = msg.get('params') or {}
    if method == 'initialize':
        reply(mid, {'protocolVersion': params.get('protocolVersion', '2025-06-18'),
                    'capabilities': {'tools': {'listChanged': False}},
                    'serverInfo': {'name': 'wc3-dota', 'version': VERSION},
                    'instructions': INSTRUCTIONS})
    elif method == 'tools/list':
        reply(mid, {'tools': [{k: v for k, v in t.items() if k != 'fn'} for t in TOOLS]})
    elif method == 'tools/call':
        name = params.get('name')
        tool = next((t for t in TOOLS if t['name'] == name), None)
        if tool is None:
            reply(mid, error={'code': -32602, 'message': 'unknown tool %s' % name})
            return
        try:
            text = tool['fn'](params.get('arguments') or {})
            reply(mid, {'content': [{'type': 'text', 'text': text}], 'isError': False})
        except GameError as e:
            reply(mid, {'content': [{'type': 'text', 'text': str(e)}], 'isError': True})
        except Exception as e:
            log('ERROR', name, traceback.format_exc())
            reply(mid, {'content': [{'type': 'text', 'text': 'internal error: %r' % e}], 'isError': True})
    elif method == 'ping':
        reply(mid, {})
    elif mid is not None and method:
        if method.startswith('notifications/'):
            return
        reply(mid, error={'code': -32601, 'message': 'method not found: %s' % method})


def main():
    sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    log('server start', VERSION, 'WC3 =', WC3)
    for line in sys.stdin.buffer:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode('utf-8'))
        except ValueError:
            reply(None, error={'code': -32700, 'message': 'parse error'})
            continue
        for m in (msg if isinstance(msg, list) else [msg]):
            try:
                handle(m)
            except Exception:
                log('ERROR handling', traceback.format_exc())


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--call':      # manual testing: server.py --call tool '{"k":"v"}' | @args.json
        t = next(t for t in TOOLS if t['name'] == sys.argv[2])
        a = sys.argv[3] if len(sys.argv) > 3 else '{}'
        if a.startswith('@'):
            a = open(a[1:], encoding='utf-8-sig').read()
        try:
            print(t['fn'](json.loads(a)))
        except GameError as e:
            print('ERROR:', e)
    else:
        main()
