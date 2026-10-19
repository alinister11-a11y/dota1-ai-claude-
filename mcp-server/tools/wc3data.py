"""Readers for WC3 object data as stored in maps: SYLK tables (.slk) and INI-style .txt profiles."""
import re


def read_slk(data):
    """Return {row_key: {column_name: value}} keyed by the first column."""
    text = data.decode('utf-8', 'replace') if isinstance(data, bytes) else data
    cells = {}
    x = y = 0
    for line in text.splitlines():
        if not line.startswith('C;') and not line.startswith('F;'):
            continue
        parts = line.split(';')
        val = None
        for p in parts[1:]:
            if not p:
                continue
            if p[0] == 'X':
                x = int(p[1:])
            elif p[0] == 'Y':
                y = int(p[1:])
            elif p[0] == 'K' and parts[0] == 'C':
                val = p[1:]
        if parts[0] == 'C' and val is not None:
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            cells[(y, x)] = val
    header = {x: v for (y, x), v in cells.items() if y == 1}
    rows = {}
    for (y, x), v in cells.items():
        if y == 1:
            continue
        rows.setdefault(y, {})[header.get(x, 'col%d' % x)] = v
    out = {}
    first = min(header) if header else 1
    key_col = header.get(first)
    for y, r in rows.items():
        k = r.get(key_col)
        if k:
            out[k] = r
    return out


def read_profile(data, into=None):
    """INI-like [ID] sections with key=value lines; later files do not override earlier keys."""
    text = data.decode('utf-8', 'replace') if isinstance(data, bytes) else data
    out = {} if into is None else into
    sec = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        if line.startswith('[') and line.endswith(']'):
            sec = out.setdefault(line[1:-1], {})
            continue
        if sec is not None and '=' in line:
            k, v = line.split('=', 1)
            sec.setdefault(k.strip(), v.strip())
    return out


COLOR = re.compile(r'\|c[0-9a-fA-F]{8}|\|r|\|n')


def clean(s):
    if s is None:
        return ''
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return COLOR.sub(' ', s).replace('  ', ' ').strip()


def first(s):
    """First entry of a comma list, respecting quotes."""
    s = (s or '').strip()
    if s.startswith('"'):
        e = s.find('"', 1)
        return s[1:e] if e > 0 else s[1:]
    return s.split(',')[0]
