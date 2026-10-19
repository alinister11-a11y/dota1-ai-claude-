"""Unified diff of two JASS scripts with enclosing function names. Usage: jdiff.py a.j b.j [max_lines]"""
import difflib, re, sys
sys.stdout.reconfigure(encoding='utf-8')
a = open(sys.argv[1], encoding='utf-8', errors='replace').read().replace('\r\n', '\n').split('\n')
b = open(sys.argv[2], encoding='utf-8', errors='replace').read().replace('\r\n', '\n').split('\n')
mx = int(sys.argv[3]) if len(sys.argv) > 3 else 400
fn_b = []
cur = ''
for l in b:
    m = re.match(r'function (\w+)', l)
    if m:
        cur = m.group(1)
    fn_b.append(cur)
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
n = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        continue
    print('@@ %s a%d-%d b%d-%d [%s]' % (tag, i1 + 1, i2, j1 + 1, j2, fn_b[j1] if j1 < len(fn_b) else ''))
    for l in a[i1:i2][:12]:
        print('- ' + l[:200]); n += 1
    if i2 - i1 > 12: print('- ... (%d lines)' % (i2 - i1))
    for l in b[j1:j2][:12]:
        print('+ ' + l[:200]); n += 1
    if j2 - j1 > 12: print('+ ... (%d lines)' % (j2 - j1))
    if n > mx:
        print('... truncated'); break
