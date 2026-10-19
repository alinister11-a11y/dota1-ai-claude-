"""grep a JASS file, printing line number, enclosing function and (trimmed) line.
Usage: python -I jgrep.py <file.j> <regex> [maxhits] [width] [exclude_regex]
"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
path, pat = sys.argv[1], re.compile(sys.argv[2])
maxhits = int(sys.argv[3]) if len(sys.argv) > 3 else 200
width = int(sys.argv[4]) if len(sys.argv) > 4 else 180
excl = re.compile(sys.argv[5]) if len(sys.argv) > 5 else None
fn = ''
n = 0
for i, line in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
    m = re.match(r'function (\w+)', line)
    if m:
        fn = m.group(1)
    if pat.search(line) and not (excl and excl.search(line)):
        print('%6d [%s] %s' % (i, fn, line.rstrip()[:width]))
        n += 1
        if n >= maxhits:
            print('... (max hits)')
            break
