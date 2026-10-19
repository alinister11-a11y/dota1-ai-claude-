"""Make the "vs Claude" build of a DotA AI map.

- every GetPlayerController( in the map script becomes AzCtl(, which reports Claude's computer slot
  as a human while Claude is steering it, so the map's own AI leaves that hero alone;
- the bridge from bridge.j is injected (file I/O with the MCP server, synced over LAN);
- the map is renamed so it is easy to find in the LAN map list.

Usage: python -I patch_map.py <wc3_dir> <in.w3x> <out.w3x> [--name "Map name"]
"""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import MPQ

args = sys.argv[1:]
name = 'DotA 6.88f AI vs Claude'
if '--name' in args:
    i = args.index('--name'); name = args[i + 1]; del args[i:i + 2]
wc3, src, dst = args
if os.path.exists(dst):
    sys.exit('refusing to overwrite ' + dst)

m = MPQ(src)
script_name = next(n for n in ('scripts\\war3map.j', 'war3map.j') if m.find(n) is not None)
raw = m.read(script_name)
bom = raw.startswith(b'\xef\xbb\xbf')
text = raw[3:].decode('utf-8') if bom else raw.decode('utf-8')
EOL = '\r\n' if '\r\n' in text else '\n'

bridge = open(os.path.join(HERE, 'bridge.j'), encoding='utf-8').read().replace('\r\n', '\n')
parts = dict(re.findall(r'//@(\w+)\n(.*?)(?=//@\w+\n|\Z)', bridge, re.S))
GLOB, CTL, FUNCS = parts['GLOBALS'].strip('\n'), parts['CTL'].strip('\n'), parts['FUNCS'].strip('\n')

# ---- lint the injected code: block balance and that every call target exists before use
def natives_and_functions(path_list):
    names = set()
    for arc in ('War3Patch.mpq', 'War3x.mpq', 'war3.mpq'):
        a = MPQ(os.path.join(wc3, arc))
        for p in path_list:
            d = a.read(p)
            if d:
                names |= set(re.findall(r'^\s*(?:constant\s+)?(?:native|function)\s+(\w+)', d.decode('latin-1'), re.M))
    return names

known = natives_and_functions(['Scripts\\common.j', 'Scripts\\Blizzard.j'])
map_funcs = set(re.findall(r'^function (\w+)', text, re.M))
def lint(code, label):
    depth = []
    defined = set()
    for ln, line in enumerate(code.split('\n'), 1):
        s = line.strip()
        mm = re.match(r'function (\w+)', s)
        if mm:
            defined.add(mm.group(1)); depth.append('function')
        for kw, close in (('if', 'endif'), ('loop', 'endloop')):
            if re.match(r'%s\b' % kw, s): depth.append(kw)
            if s == close:
                if not depth or depth.pop() != kw: sys.exit('%s:%d unbalanced %s' % (label, ln, close))
        if s == 'endfunction':
            if not depth or depth.pop() != 'function': sys.exit('%s:%d unbalanced endfunction' % (label, ln))
        for call in re.findall(r'\b([A-Za-z_]\w*)\s*\(', re.sub(r'"(?:\\.|[^"\\])*"', '""', s)):
            if call in ('if', 'not', 'and', 'or', 'function', 'return', 'set', 'call', 'local', 'exitwhen', 'elseif'):
                continue
            if call not in known and call not in map_funcs and call not in defined:
                sys.exit('%s:%d unknown function %s' % (label, ln, call))
    if depth: sys.exit('%s: unclosed %s' % (label, depth))
lint(CTL, 'CTL'); lint(FUNCS, 'FUNCS')
ours = set(re.findall(r'^\s*\w+(?:\s+array)?\s+(\w+)', GLOB, re.M)) | set(re.findall(r'^function (\w+)', CTL + '\n' + FUNCS, re.M))
clash = sorted(ours & set(re.findall(r'\b[A-Za-z_]\w*\b', text)))
if clash:
    sys.exit('names already used by the map: %s' % clash)
# a local or parameter named like a map global silently breaks the 1.27 script compiler
gnames = set(re.findall(r'^\s*(?:constant\s+)?\w+(?:\s+array)?\s+(\w+)', text[:text.index('endglobals')], re.M))
locs = set(re.findall(r'^local\s+\w+\s+(\w+)', FUNCS + '\n' + CTL, re.M))
locs |= {x for a in re.findall(r'takes (.*?) returns', FUNCS + '\n' + CTL) if a != 'nothing' for x in re.findall(r'\w+\s+(\w+)', a)}
if locs & gnames:
    sys.exit('locals/parameters shadow map globals: %s' % sorted(locs & gnames))
types = {'integer', 'real', 'boolean', 'string', 'handle', 'code', 'nothing'}
for arc in ('War3Patch.mpq', 'war3.mpq'):
    d = MPQ(os.path.join(wc3, arc)).read('Scripts\\common.j')
    if d:
        types |= set(re.findall(r'^type\s+(\w+)', d.decode('latin-1'), re.M))
ournames = locs | ours
if ournames & types:
    sys.exit('variables named like JASS types: %s' % sorted(ournames & types))
needed = {'M7', 'K34', 'K54', 'J', 'eY', 'KZ4', 'Z7', 'A7', 'ED', 'L9'}
gl = text[:text.index('endglobals')]
missing = [g for g in needed if not re.search(r'^\s*\w+(\s+array)?\s+%s\b' % g, gl, re.M)]
if missing:
    sys.exit('map globals not found: %s' % missing)

# ---- patch the script (AZ_STAGE for bisecting: 0 = rename only, 1 = + controller wrapper,
#      2 = + bridge functions, 3 = full with AzInit started from main)
stage = int(os.environ.get('AZ_STAGE', '3'))
def wrap_force_calls(text, fn, new, force='QX4'):
    """Rename fn(...,QX4) calls (the map's AI-player force) to new(...); args may nest parentheses."""
    out, i, n = [], 0, 0
    pat = fn + '('
    while True:
        j = text.find(pat, i)
        if j < 0:
            out.append(text[i:])
            return ''.join(out), n
        if j > 0 and (text[j - 1].isalnum() or text[j - 1] == '_'):
            out.append(text[i:j + len(pat)])
            i = j + len(pat)
            continue
        k, depth = j + len(pat), 1
        while depth:
            depth += {'(': 1, ')': -1}.get(text[k], 0)
            k += 1
        args = text[j + len(pat):k - 1]
        if args.replace(' ', '').endswith(',' + force):
            out.append(text[i:j] + new + '(' + args + ')')
            n += 1
        else:
            out.append(text[i:k])
        i = k


nrep = 0
if stage >= 1:
    text, nrep = re.subn(r'\bGetPlayerController\(', 'AzCtl(', text)
    text, n1 = wrap_force_calls(text, 'IsPlayerInForce', 'AzPInAI')
    text, n2 = wrap_force_calls(text, 'IsUnitInForce', 'AzUInAI')
    print('AI-force checks wrapped: %d player, %d unit' % (n1, n2))

    # keep the map's AI from giving Claude's slot a random hero while Claude may still pick one
    def patch_in_function(text, fname, old, new, count):
        s = text.index('function %s takes' % fname)
        e = text.index(EOL + 'endfunction', s)
        body = text[s:e]
        if body.count(old) != count:
            sys.exit('pick hook: expected %d x %r in %s, found %d' % (count, old, fname, body.count(old)))
        return text[:s] + body.replace(old, new) + text[e:]
    text = patch_in_function(text, 'XZE', 'and(M7[GetPlayerId(pl)]==null))then',
                             'and(M7[GetPlayerId(pl)]==null)and not(AzNoAIPick and pl==AzCP))then', 1)
    text = patch_in_function(text, 'PJ9', 'if TZ7(Z7[i])then', 'if TZ7(Z7[i])and not(AzNoAIPick and Z7[i]==AzCP)then', 1)
    text = patch_in_function(text, 'PJ9', 'if TZ7(A7[i])then', 'if TZ7(A7[i])and not(AzNoAIPick and A7[i]==AzCP)then', 1)
    gi = text.index(EOL + 'endglobals')
    text = text[:gi] + EOL + GLOB.replace('\n', EOL) + text[gi:]
    ge = text.index('endglobals' + EOL) + len('endglobals' + EOL)
    text = text[:ge] + CTL.replace('\n', EOL) + EOL + text[ge:]
    # the map's display-name helper: announce Claude's picks/kills as "Claude"
    vt = 'function VT7 takes player p returns string' + EOL + 'return KZ4[GetPlayerId(p)]'
    if vt in text:
        text = text.replace(vt, vt.split(EOL)[0] + EOL + 'if p==AzCP then' + EOL + 'return "Claude"' + EOL +
                            'endif' + EOL + vt.split(EOL)[1], 1)
    else:
        print('note: name helper VT7 not found; announcements may show the computer name')
if stage >= 2:
    mi = text.index(EOL + 'function main takes nothing returns nothing') + len(EOL)
    text = text[:mi] + FUNCS.replace('\n', EOL) + EOL + text[mi:]
if stage >= 3:
    mi = text.index(EOL + 'function main takes nothing returns nothing')
    me = text.index(EOL + 'endfunction', mi)
    text = text[:me] + EOL + 'call ExecuteFunc("AzInit")' + text[me:]

tmp = tempfile.mkdtemp(prefix='azpatch_')
jpath = os.path.join(tmp, 'war3map.j')
with open(jpath, 'wb') as f:
    f.write((b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8'))

repl = ['%s=%s' % (script_name, jpath)]
wts = m.read('war3map.wts')
if wts is not None:
    w = wts.decode('utf-8-sig')
    mm = re.search(r'TRIGSTR_(\d+)', m.read('war3map.w3i')[12:60].decode('latin-1'))
    if mm:
        w2 = re.sub(r'(STRING %s\s*\{\s*)(.*?)(\s*\})' % mm.group(1), lambda x: x.group(1) + name + x.group(3), w, count=1, flags=re.S)
        wpath = os.path.join(tmp, 'war3map.wts')
        with open(wpath, 'wb') as f:
            f.write((b'\xef\xbb\xbf' if wts.startswith(b'\xef\xbb\xbf') else b'') + w2.encode('utf-8'))
        repl.append('war3map.wts=%s' % wpath)

print('GetPlayerController calls wrapped: %d' % nrep)
r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'compact.py'), src, dst] + repl)
if r.returncode:
    sys.exit(r.returncode)
# the LAN map list shows the name stored in the HM3W file header, not the one in war3map.w3i
with open(dst, 'r+b') as f:
    head = bytearray(f.read(512))
    if head[:4] == b'HM3W':
        end = head.index(0, 8)
        rest = head[end + 1:end + 9]                       # map flags + max players
        new = b'HM3W' + head[4:8] + name.encode('utf-8') + b'\0' + rest
        if len(new) <= m.base:
            f.seek(0)
            f.write(new + b'\0' * (min(512, m.base) - len(new)))
            print('map list name: %s' % name)
