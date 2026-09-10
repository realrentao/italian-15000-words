#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Row-type-aware scan of ALL sec files for:
- leading number in the Italian field (w/e: field[1]; s: field[0])
- grammar token merged into the Italian field while 词性 empty
- grammar token duplicated in Italian field and 词性
Handles w/e rows [zh,it,pos,...] and s rows [it,zh,src,...].
"""
import glob, re, os

GRAMMAR = r'(?:v\.tr\.|v\.intr\.|v\.rifl\.|s\.m\.|s\.f\.|n\.m\.|n\.|agg\.|avv\.)'
CJK = re.compile(r'[一-鿿]')
ROW = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
    r'"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)

A = []; B = []; C = []
for f in sorted(glob.glob('data/sec/*.js')):
    src = open(f, encoding='utf-8').read()
    for m in ROW.finditer(src):
        g = m.groups()
        base = os.path.basename(f)
        # decide row type by whether field[0] is Chinese
        if CJK.search(g[0]):          # w/e row -> Italian is field[1], pos is field[2]
            it, pos = g[1], g[2]
        else:                          # s row -> Italian is field[0], "pos" n/a
            it, pos = g[0], ''
        if re.match(r'^\d+\s+', it):
            A.append((base, it))
        if pos == '' and re.search(r'\s+' + GRAMMAR + r'$', it):
            B.append((base, it))
        if pos != '' and re.search(r'\s+' + GRAMMAR + r'$', it):
            C.append((base, it, pos))

print('A. leading-number in Italian field :', len(A))
print('B. grammar merged, pos empty       :', len(B))
print('C. grammar dup (word+pos)          :', len(C))
for x in A: print('  A', x)
for x in B: print('  B', x)
for x in C: print('  C', x)
