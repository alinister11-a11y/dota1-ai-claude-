"""Minimal read-only MPQ (v1) extractor for Warcraft III maps.
Usage: python -I mpq.py <map.w3x> <outdir> [name ...]
"""
import os, struct, sys, zlib, bz2

def _crypt_table():
    t = [0] * 0x500
    seed = 0x00100001
    for i1 in range(0x100):
        i2 = i1
        for _ in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            a = (seed & 0xFFFF) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            b = seed & 0xFFFF
            t[i2] = a | b
            i2 += 0x100
    return t

CT = _crypt_table()
M = 0xFFFFFFFF

def hs(s, kind):
    s1, s2 = 0x7FED7FED, 0xEEEEEEEE
    for ch in s.upper().replace('/', '\\').encode('latin-1'):
        s1 = (CT[(kind << 8) + ch] ^ ((s1 + s2) & M)) & M
        s2 = (ch + s1 + s2 + (s2 << 5) + 3) & M
    return s1

def decrypt(data, key):
    n = len(data) // 4
    vals = struct.unpack('<%dI' % n, data[:n * 4])
    out = []
    s1, s2 = key, 0xEEEEEEEE
    for v in vals:
        s2 = (s2 + CT[0x400 + (s1 & 0xFF)]) & M
        c = (v ^ ((s1 + s2) & M)) & M
        out.append(c)
        s1 = (((~s1 & M) << 0x15) + 0x11111111 | (s1 >> 0x0B)) & M
        s2 = (c + s2 + (s2 << 5) + 3) & M
    return struct.pack('<%dI' % n, *out) + data[n * 4:]

# --- PKWare DCL explode (port of zlib's blast.c) ---
def explode(data):
    pos = [0]; bitbuf = [0]; bitcnt = [0]
    def bits(need):
        val = bitbuf[0]
        while bitcnt[0] < need:
            val |= data[pos[0]] << bitcnt[0]; pos[0] += 1; bitcnt[0] += 8
        bitbuf[0] = val >> need; bitcnt[0] -= need
        return val & ((1 << need) - 1)
    def construct(rep):
        lengths = []
        for r in rep:
            lengths += [r & 15] * ((r >> 4) + 1)
        count = [0] * 14
        for l in lengths: count[l] += 1
        offs = [0] * 14
        for l in range(1, 13): offs[l + 1] = offs[l] + count[l]
        symbol = [0] * len(lengths)
        for s, l in enumerate(lengths):
            if l: symbol[offs[l]] = s; offs[l] += 1
        return count, symbol
    def decode(h):
        count, symbol = h
        code = first = index = 0
        for l in range(1, 14):
            code |= bits(1) ^ 1
            c = count[l]
            if code < first + c: return symbol[index + (code - first)]
            index += c; first += c; first <<= 1; code <<= 1
        raise ValueError('bad code')
    litlen = [11,124,8,7,28,7,188,13,76,4,10,8,12,10,12,10,8,23,8,9,7,6,7,8,7,6,55,8,23,24,12,11,7,9,11,12,6,7,22,5,7,24,6,11,9,6,7,22,7,11,38,7,9,8,25,11,8,11,9,12,8,12,5,38,5,38,5,11,7,5,6,21,6,10,53,8,7,24,10,27,44,253,253,253,252,252,252,13,12,45,12,45,12,61,12,45,44,173]
    lenlen = [2,35,36,53,38,23]
    distlen = [2,20,53,230,247,151,248]
    base = [3,2,4,5,6,7,8,9,10,12,16,24,40,72,136,264]
    extra = [0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8]
    hlit, hlen, hdist = construct(litlen), construct(lenlen), construct(distlen)
    lit = bits(8); dictb = bits(8)
    out = bytearray()
    while True:
        if bits(1):
            sym = decode(hlen)
            ln = base[sym] + bits(extra[sym])
            if ln == 519: break
            sym = 2 if ln == 2 else dictb
            dist = (decode(hdist) << sym) + bits(sym) + 1
            for _ in range(ln): out.append(out[-dist])
        else:
            out.append(decode(hlit) if lit else bits(8))
    return bytes(out)

def decompress(buf, outsize):
    if len(buf) >= outsize:
        return buf[:outsize]
    mask = buf[0]; d = buf[1:]
    if mask & 0x10: d = bz2.decompress(d)
    if mask & 0x08: d = explode(d)
    if mask & 0x02: d = zlib.decompress(d)
    if mask & ~0x1A:
        raise ValueError('unsupported compression mask 0x%02X' % mask)
    return d

class MPQ:
    def __init__(self, path):
        self.f = open(path, 'rb')
        raw = self.f.read()
        self.raw = raw
        self.base = raw.find(b'MPQ\x1a')
        while self.base % 512:
            self.base = raw.find(b'MPQ\x1a', self.base + 1)
        hdr = raw[self.base:self.base + 32]
        (_, self.hsize, self.asize, self.ver, shift,
         hpos, bpos, hcount, bcount) = struct.unpack('<4sIIHHIIII', hdr)
        self.sector = 512 << shift
        ht = decrypt(raw[self.base + hpos:self.base + hpos + hcount * 16], hs('(hash table)', 3))
        bt = decrypt(raw[self.base + bpos:self.base + bpos + bcount * 16], hs('(block table)', 3))
        self.hash = [struct.unpack_from('<IIHHI', ht, i * 16) for i in range(hcount)]
        self.block = [struct.unpack_from('<IIII', bt, i * 16) for i in range(bcount)]
        self.hcount, self.bcount = hcount, bcount

    def find(self, name):
        i = hs(name, 0) & (self.hcount - 1)
        a, b = hs(name, 1), hs(name, 2)
        for _ in range(self.hcount):
            n1, n2, loc, plat, bi = self.hash[i]
            if bi == 0xFFFFFFFF: return None
            if n1 == a and n2 == b and bi < self.bcount: return bi
            i = (i + 1) & (self.hcount - 1)
        return None

    def read(self, name):
        bi = self.find(name)
        if bi is None: return None
        pos, csize, fsize, flags = self.block[bi]
        data = self.raw[self.base + pos:self.base + pos + csize]
        key = None
        if flags & 0x10000:
            key = hs(name.replace('/', '\\').split('\\')[-1], 3)
            if flags & 0x20000: key = ((key + pos) ^ fsize) & M
        if flags & 0x01000000:  # single unit
            if key is not None: data = decrypt(data, key)
            return decompress(data, fsize) if flags & 0x300 else data[:fsize]
        if not flags & 0x300:
            if key is None: return data[:fsize]
            out = bytearray()
            for s in range(0, fsize, self.sector):
                out += decrypt(data[s:s + self.sector], (key + s // self.sector) & M)
            return bytes(out[:fsize])
        ns = (fsize + self.sector - 1) // self.sector
        otab = data[:(ns + 1) * 4]
        if key is not None: otab = decrypt(otab, (key - 1) & M)
        offs = struct.unpack('<%dI' % (ns + 1), otab)
        out = bytearray()
        for s in range(ns):
            chunk = data[offs[s]:offs[s + 1]]
            if key is not None: chunk = decrypt(chunk, (key + s) & M)
            want = min(self.sector, fsize - s * self.sector)
            if flags & 0x100:
                out += explode(chunk) if len(chunk) < want else chunk
            else:
                out += decompress(chunk, want)
        return bytes(out[:fsize])

if __name__ == '__main__':
    mp, outdir = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or ['(listfile)', 'war3map.j', 'scripts\\war3map.j',
                             'war3map.w3i', '(attributes)', 'war3map.wts']
    m = MPQ(mp)
    print('base=%d sector=%d hash=%d block=%d' % (m.base, m.sector, m.hcount, m.bcount))
    os.makedirs(outdir, exist_ok=True)
    for n in names:
        try:
            d = m.read(n)
        except Exception as e:
            print('%-22s ERROR %r' % (n, e)); continue
        if d is None:
            print('%-22s not found' % n); continue
        bi = m.find(n)
        print('%-22s %8d bytes  flags=0x%08X' % (n, len(d), m.block[bi][3]))
        with open(os.path.join(outdir, n.replace('\\', '_')), 'wb') as fh:
            fh.write(d)
