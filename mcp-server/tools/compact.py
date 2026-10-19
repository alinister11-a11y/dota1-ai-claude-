"""Rebuild an MPQ map without its unused gap bytes, optionally replacing some files.
Blocks are copied byte-for-byte in their original order; files whose encryption key depends on
their position (FIX_KEY) are re-encrypted for their new position. Replaced files are stored
zlib-compressed and unencrypted.
Usage: compact.py in.w3x out.w3x [mpq_name=local_file ...]
"""
import os, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mpq import MPQ, CT, M, hs, decrypt

def encrypt(data, key):
    n = len(data) // 4
    vals = struct.unpack('<%dI' % n, data[:n * 4])
    out = []; s1, s2 = key, 0xEEEEEEEE
    for v in vals:
        s2 = (s2 + CT[0x400 + (s1 & 0xFF)]) & M
        out.append((v ^ ((s1 + s2) & M)) & M)
        s1 = (((~s1 & M) << 0x15) + 0x11111111 | (s1 >> 0x0B)) & M
        s2 = (v + s2 + (s2 << 5) + 3) & M
    return struct.pack('<%dI' % n, *out) + data[n * 4:]

def pack_sectors(data, sector):
    ns = max(1, (len(data) + sector - 1) // sector)
    chunks = []
    for i in range(ns):
        raw = data[i * sector:(i + 1) * sector]
        c = zlib.compress(raw, 9)
        chunks.append(b'\x02' + c if len(c) + 1 < len(raw) else raw)
    offs = [(ns + 1) * 4]
    for c in chunks: offs.append(offs[-1] + len(c))
    return struct.pack('<%dI' % (ns + 1), *offs) + b''.join(chunks)

def rekey(raw, flags, fsize, basekey, oldpos, newpos, sector):
    k_old = ((basekey + oldpos) ^ fsize) & M
    k_new = ((basekey + newpos) ^ fsize) & M
    if flags & 0x01000000 or not flags & 0x300:          # single unit / uncompressed: sectors back to back
        if flags & 0x01000000:
            return encrypt(decrypt(raw, k_old), k_new)
        out = bytearray()
        for i, s in enumerate(range(0, len(raw), sector)):
            out += encrypt(decrypt(raw[s:s + sector], (k_old + i) & M), (k_new + i) & M)
        return bytes(out)
    ns = (fsize + sector - 1) // sector
    tbl_len = (ns + 1) * 4
    offs = struct.unpack('<%dI' % (ns + 1), decrypt(raw[:tbl_len], (k_old - 1) & M))
    out = bytearray(encrypt(struct.pack('<%dI' % (ns + 1), *offs), (k_new - 1) & M))
    out += raw[tbl_len:offs[0]]
    for i in range(ns):
        out += encrypt(decrypt(raw[offs[i]:offs[i + 1]], (k_old + i) & M), (k_new + i) & M)
    out += raw[offs[ns]:]
    assert len(out) == len(raw)
    return bytes(out)

src, dst = sys.argv[1], sys.argv[2]
if os.path.exists(dst): sys.exit('refusing to overwrite ' + dst)
repl = dict(a.split('=', 1) for a in sys.argv[3:])
m = MPQ(src)
names = [n for n in m.read('(listfile)').decode('utf-8', 'replace').replace('\r', '').split('\n') if n.strip()] + ['(listfile)', '(attributes)', '(signature)']
name_of = {}
for n in names:
    bi = m.find(n)
    if bi is not None: name_of.setdefault(bi, n)
repl_blocks = {}
for n, local in repl.items():
    bi = m.find(n)
    if bi is None: sys.exit('not in archive: ' + n)
    repl_blocks[bi] = open(local, 'rb').read()
# WC3 verifies each file's CRC32 from (attributes): refresh the CRCs of replaced files
abi = m.find('(attributes)')
if abi is not None and abi not in repl_blocks:
    attr = bytearray(m.read('(attributes)'))
    aver, aflags = struct.unpack_from('<II', attr)
    if aflags & 1 and len(attr) >= 8 + 4 * m.bcount:
        for bi, data in repl_blocks.items():
            struct.pack_into('<I', attr, 8 + 4 * bi, zlib.crc32(data) & M)
        repl_blocks[abi] = bytes(attr)
base = m.base
out = bytearray(m.raw[:base + 32])           # HM3W header + MPQ header (patched below)
blocks = [list(b) for b in m.block]
order = sorted(range(m.bcount), key=lambda i: m.block[i][0])
for bi in order:
    pos, cs, fs, fl = m.block[bi]
    if not fl & 0x80000000: continue
    newpos = len(out) - base
    if bi in repl_blocks:
        data = repl_blocks[bi]
        packed = pack_sectors(data, m.sector)
        out += packed
        blocks[bi] = [newpos, len(packed), len(data), 0x80000200]
        continue
    raw = m.raw[base + pos:base + pos + cs]
    if fl & 0x10000 and fl & 0x20000 and cs:
        n = name_of[bi]                       # every FIX_KEY block has a known name (checked)
        raw = rekey(raw, fl, fs, hs(n.replace('/', '\\').split('\\')[-1], 3), pos, newpos, m.sector)
    out += raw
    blocks[bi][0] = newpos
hpos = len(out) - base
out += encrypt(b''.join(struct.pack('<IIHHI', *h) for h in m.hash), hs('(hash table)', 3))
bpos = len(out) - base
out += encrypt(b''.join(struct.pack('<IIII', *b) for b in blocks), hs('(block table)', 3))
struct.pack_into('<I', out, base + 8, len(out) - base)
struct.pack_into('<II', out, base + 16, hpos, bpos)
with open(dst, 'xb') as fh: fh.write(out)
print('wrote %s: %.1f MB (was %.1f MB), replaced %d file(s)' % (dst, len(out) / 1e6, len(m.raw) / 1e6, len(repl)))
