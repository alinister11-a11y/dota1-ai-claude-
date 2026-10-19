"""Editing helpers for WC3 map data: SLK row appends, txt profile edits, and a from-scratch MPQ writer."""
import os, re, struct, zlib, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server', 'tools'))
from mpq import CT, M, hs


def _num(v):
    return re.fullmatch(r'-?\d+(\.\d*)?|-?\.\d+', v) is not None


def slk_append(data, rows):
    """Append rows ({column: value}, first key = id column) to an SLK table, adding columns if needed."""
    text = data.decode('latin-1')
    eol = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(eol)
    header = {}
    x = y = 0
    last_hdr = None
    maxx = maxy = 0
    for i, line in enumerate(lines):
        if not line.startswith('C;'):
            continue
        val = None
        for p in line.split(';')[1:]:
            if p[:1] == 'X':
                x = int(p[1:])
            elif p[:1] == 'Y':
                y = int(p[1:])
            elif p[:1] == 'K':
                val = p[1:]
        maxx = max(maxx, x); maxy = max(maxy, y)
        if y == 1 and val is not None:
            header[val.strip('"')] = x
            last_hdr = i
    new_hdr = []
    for r in rows:
        for k in r:
            if k not in header:
                maxx += 1
                header[k] = maxx
                new_hdr.append('C;X%d;K"%s"' % (maxx, k))
    out_rows = []
    for r in rows:
        maxy += 1
        first = True
        for k, v in r.items():
            v = str(v)
            cell = 'K%s' % v if _num(v) else 'K"%s"' % v.replace('"', "'")
            if first:
                out_rows.append('C;Y%d;X%d;%s' % (maxy, header[k], cell))
                first = False
            else:
                out_rows.append('C;X%d;%s' % (header[k], cell))
    lines = lines[:last_hdr + 1] + new_hdr + lines[last_hdr + 1:]
    e = max(i for i, l in enumerate(lines) if l == 'E')
    lines = lines[:e] + out_rows + lines[e:]
    for i, l in enumerate(lines):
        if l.startswith('B;'):
            lines[i] = 'B;Y%d;X%d;D0 0 %d %d' % (maxy, maxx, maxy - 1, maxx - 1)
    return eol.join(lines).encode('latin-1')


def slk_header(data):
    text = data.decode('latin-1')
    cols = []
    for m in re.finditer(r'^C;(?:Y1;)?X(\d+);(?:Y1;)?K"([^"]*)"', text, re.M):
        cols.append(m.group(2))
        if len(cols) > 400:
            break
    return cols


def profile_append(data, sections):
    """sections: list of (id, [(key, value), ...]); values are written as-is."""
    eol = b'\r\n' if b'\r\n' in data else b'\n'
    add = []
    for sid, kv in sections:
        add.append('[%s]' % sid)
        for k, v in kv:
            add.append('%s=%s' % (k, v))
    return data.rstrip(b'\r\n') + eol + eol.join(a.encode('utf-8') for a in add) + eol


def profile_set(data, sid, key, fn):
    """Replace key's value in section [sid] with fn(old)."""
    text = data.decode('latin-1')
    eol = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(eol)
    sec = None
    done = False
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith('[') and s.endswith(']'):
            sec = s[1:-1]
            continue
        if sec == sid and '=' in s and s.split('=', 1)[0].strip().lower() == key.lower():
            k, v = l.split('=', 1)
            lines[i] = k + '=' + fn(v)
            done = True
    if not done:
        raise KeyError('%s/%s not found' % (sid, key))
    return eol.join(lines).encode('latin-1')


def _encrypt(data, key):
    n = len(data) // 4
    vals = struct.unpack('<%dI' % n, data[:n * 4])
    out = []; s1, s2 = key, 0xEEEEEEEE
    for v in vals:
        s2 = (s2 + CT[0x400 + (s1 & 0xFF)]) & M
        out.append((v ^ ((s1 + s2) & M)) & M)
        s1 = (((~s1 & M) << 0x15) + 0x11111111 | (s1 >> 0x0B)) & M
        s2 = (v + s2 + (s2 << 5) + 3) & M
    return struct.pack('<%dI' % n, *out) + data[n * 4:]


def write_mpq(path, prefix, files, sector_shift=3):
    """Write a new MPQ v1 archive. prefix = bytes placed before the archive (HM3W header, len % 512 == 0).
    files = list of (name, data). A (listfile) is added automatically."""
    assert len(prefix) % 512 == 0
    names = [n for n, _ in files if n != '(listfile)']
    files = [(n, d) for n, d in files if n != '(listfile)']
    files.append(('(listfile)', ('\r\n'.join(names) + '\r\n').encode('utf-8')))
    sector = 512 << sector_shift
    body = bytearray(b'\0' * 32)
    blocks = []
    for name, data in files:
        pos = len(body)
        if len(data) == 0:
            blocks.append((pos, 0, 0, 0x80000000))
            continue
        ns = (len(data) + sector - 1) // sector
        chunks = []
        for i in range(ns):
            raw = data[i * sector:(i + 1) * sector]
            c = zlib.compress(raw, 9)
            chunks.append(b'\x02' + c if len(c) + 1 < len(raw) else raw)
        offs = [(ns + 1) * 4]
        for c in chunks:
            offs.append(offs[-1] + len(c))
        packed = struct.pack('<%dI' % (ns + 1), *offs) + b''.join(chunks)
        body += packed
        blocks.append((pos, len(packed), len(data), 0x80000200))
    hsize = 16
    while hsize < len(files) * 2:
        hsize *= 2
    table = [(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFF, 0xFFFF, 0xFFFFFFFF)] * hsize
    for bi, (name, _) in enumerate(files):
        i = hs(name, 0) & (hsize - 1)
        while table[i][4] != 0xFFFFFFFF:
            i = (i + 1) & (hsize - 1)
        table[i] = (hs(name, 1), hs(name, 2), 0, 0, bi)
    hpos = len(body)
    body += _encrypt(b''.join(struct.pack('<IIHHI', *h) for h in table), hs('(hash table)', 3))
    bpos = len(body)
    body += _encrypt(b''.join(struct.pack('<IIII', *b) for b in blocks), hs('(block table)', 3))
    struct.pack_into('<4sIIHHIIII', body, 0, b'MPQ\x1a', 32, len(body), 0, sector_shift, hpos, bpos, hsize, len(blocks))
    with open(path, 'xb') as f:
        f.write(prefix + bytes(body))
    return len(prefix) + len(body)
