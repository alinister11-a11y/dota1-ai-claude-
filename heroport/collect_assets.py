"""Pull model/texture/icon files out of a map that has no (listfile).
Starts from seed names, follows MDX texture (TEXS) and particle-model (PREM) references, and tries
portrait and disabled-icon name variants.
Usage: python -I collect_assets.py <map.w3x> <outdir> <seeds.txt>
"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server', 'tools'))
from mpq import MPQ

def mdx_refs(data):
    refs = []
    if data[:4] != b'MDLX':
        return refs
    p = 4
    while p + 8 <= len(data):
        tag = data[p:p + 4]; size, = struct.unpack_from('<I', data, p + 4)
        body = data[p + 8:p + 8 + size]
        if tag == b'TEXS':
            for i in range(0, len(body) - 267, 268):
                path = body[i + 4:i + 264].split(b'\0')[0].decode('latin-1')
                if path:
                    refs.append(path)
        elif tag == b'PREM':
            q = 0
            while q + 4 <= len(body):
                isz, = struct.unpack_from('<I', body, q)
                ent = body[q:q + isz]
                # node (inclusive size), then emissionRate, gravity, longitude, latitude, then the 260-byte path
                nsz, = struct.unpack_from('<I', ent, 4)
                o = 4 + nsz + 16
                path = ent[o:o + 260].split(b'\0')[0].decode('latin-1')
                if path:
                    refs.append(path)
                q += isz if isz else len(body)
        p += 8 + size
    return refs

m = MPQ(sys.argv[1])
out = sys.argv[2]
seeds = [l.strip() for l in open(sys.argv[3], encoding='utf-8') if l.strip() and not l.startswith('#')]
found, missing = {}, []
queue = list(seeds)
seen = set()

def variants(n):
    n = n.replace('/', '\\').replace('\\\\', '\\')
    base, ext = os.path.splitext(n)
    out_ = [n]
    if ext.lower() in ('.mdl', '.mdx'):
        out_ = [base + '.mdx', base + '.MDX', base + '.mdl', n]
    elif ext == '':
        out_ = [n + '.mdx', n + '.MDX', n + '.blp', n]
    elif ext.lower() == '.tga':
        out_ = [base + '.blp', n]
    return out_

while queue:
    n = queue.pop(0)
    key = n.lower()
    if key in seen:
        continue
    seen.add(key)
    hit = None
    for v in variants(n):
        bi = m.find(v)
        if bi is not None:
            hit = v
            break
    if not hit:
        missing.append(n)
        continue
    data = m.read(hit)
    found[hit] = len(data)
    dst = os.path.join(out, hit)
    os.makedirs(os.path.dirname(dst) or out, exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(data)
    base, ext = os.path.splitext(hit)
    if ext.lower() == '.mdx':
        for r in mdx_refs(data):
            queue.append(r)
        if not base.lower().endswith('_portrait'):
            queue.append(base + '_portrait.mdx')
    if ext.lower() == '.blp' and '\\CommandButtons\\' in hit:
        queue.append(hit.replace('\\CommandButtons\\', '\\CommandButtonsDisabled\\DIS'))
    if ext.lower() == '.blp' and '\\PassiveButtons\\' in hit:
        queue.append(hit.replace('\\PassiveButtons\\', '\\CommandButtonsDisabled\\DIS'))

for k, v in sorted(found.items()):
    print('FOUND %9d %s' % (v, k))
print('total %.2f MB in %d files' % (sum(found.values()) / 1e6, len(found)))
for n in missing:
    print('MISSING', n)
