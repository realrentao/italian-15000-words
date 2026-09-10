#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove byte-identical duplicate rows within each w/e/s array of every sec file.
Keeps the first occurrence; later identical rows are dropped. Safe: duplicates
reference the same audio files, so no audio is orphaned.
"""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
    r'"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)
ARR = re.compile(r'"[wes]":\[')

def dedupe_array(cont):
    """cont = text of one w/e/s array (between the [ and the matching ])."""
    rows = list(ROW.finditer(cont))
    if not rows:
        return cont, 0
    seen = set()
    removals = []
    for r in rows:
        if r.group(0) in seen:
            removals.append(r)
        else:
            seen.add(r.group(0))
    if not removals:
        return cont, 0
    new = cont
    for r in removals[::-1]:
        a, b = r.span()
        # duplicate rows are always preceded by the array separator comma
        if a > 0 and new[a - 1] == ',':
            new = new[:a - 1] + new[b:]
        else:
            new = new[:a] + new[b + 1:]
    return new, len(removals)

def find_balanced_close(s, open_idx):
    depth = 0
    i = open_idx
    n = len(s)
    while i < n:
        c = s[i]
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

total = 0
for f in sorted(glob.glob(os.path.join(ROOT, 'data/sec/*.js'))):
    content = open(f, encoding='utf-8').read()
    result = ''
    pos = 0
    removed_any = 0
    for m in ARR.finditer(content):
        start = m.end() - 1            # index of the '['
        end = find_balanced_close(content, start)
        arr_body = content[start + 1:end]
        new_body, n = dedupe_array(arr_body)
        removed_any += n
        result += content[pos:start + 1] + new_body
        pos = end                      # skip original body + ']'
    result += content[pos:]
    if removed_any:
        open(f, 'w', encoding='utf-8').write(result)
        base = os.path.basename(f)
        print(f'{base}: removed {removed_any} duplicate rows')
        total += removed_any
print(f'Total duplicate rows removed: {total}')
