"""Dump SLK rows and profile sections for given object IDs from an extracted map folder.
Usage: python -I dump_ids.py <dir> ID [ID ...]
"""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server', 'tools'))
from wc3data import read_slk

d = sys.argv[1]
ids = sys.argv[2:]
for path in sorted(glob.glob(os.path.join(d, 'Units_*.slk'))):
    rows = read_slk(open(path, 'rb').read())
    for i in ids:
        if i in rows:
            r = {k: v for k, v in rows[i].items() if v not in ('', '-', '_', '0', '"-"', '"_"')}
            print('## %s %s: %s' % (os.path.basename(path), i, r))
for path in sorted(glob.glob(os.path.join(d, 'Units_*.txt'))):
    text = open(path, 'rb').read().decode('utf-8', 'replace')
    sec = None
    buf = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            sec = s[1:-1]
            continue
        if sec in ids and s and not s.startswith('//') and not any(s.startswith(k) for k in ('ubertip', 'researchubertip', 'tip=', 'researchtip')):
            buf.setdefault(sec, []).append(s)
    for i in ids:
        if i in buf:
            print('## %s [%s]: %s' % (os.path.basename(path), i, ' | '.join(buf[i])))
