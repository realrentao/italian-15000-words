#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deeper QA: duplicates, missing IPA/pinyin, IPA format."""
import glob, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[一-鿿]')
ROW = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
    r'"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)

exact_dup = defaultdict(list)      # normalized tuple -> list of (file, idx_in_file)
missing_ipa_we = []
missing_py_we = []
ipa_no_slash = []
empty_pos_we = []
total = 0
rowindex = defaultdict(int)  # per file running index

for f in sorted(glob.glob(os.path.join(ROOT, 'data/sec/*.js'))):
    src = open(f, encoding='utf-8').read()
    base = os.path.basename(f)
    rowindex[base] = 0
    for m in ROW.finditer(src):
        g = m.groups()
        rowindex[base] += 1
        total += 1
        f0, f1, f2, it_a, zh_a, py, ipa = g
        kind = 'we' if CJK.search(f0) else 's'
        it_text = f1 if kind == 'we' else f0
        zh_text = f0 if kind == 'we' else f1
        # exact-duplicate key (normalized by stripping spaces/lowercasing italian + chinese)
        key = (it_text.strip().lower(), zh_text.strip())
        exact_dup[key].append((base, rowindex[base], kind))
        if kind == 'we':
            if not ipa.strip():
                missing_ipa_we.append((base, rowindex[base], it_text))
            else:
                s = ipa.strip()
                if not (s.startswith('/') and s.endswith('/')):
                    ipa_no_slash.append((base, rowindex[base], it_text, s))
            if not py.strip():
                missing_py_we.append((base, rowindex[base], it_text))
            if not f2.strip():
                empty_pos_we.append((base, rowindex[base], it_text))

# keep only keys appearing >1 with >=2 distinct file/positions (true duplicates)
dups = {k: v for k, v in exact_dup.items() if len(v) > 1}

print(f'Total rows                : {total}')
print(f'Exact duplicate (it+zh)   : {len(dups)} groups, {sum(len(v) for v in dups.values())} rows')
print(f'w/e missing 音标 (IPA)     : {len(missing_ipa_we)}')
print(f'w/e missing 拼音 (pinyin)  : {len(missing_py_we)}')
print(f'IPA not wrapped in /.../  : {len(ipa_no_slash)}')
print(f'w/e empty 词性            : {len(empty_pos_we)}')

print('\n--- exact duplicate groups (sample up to 30) ---')
for k, v in list(dups.items())[:30]:
    print(f'  {k} -> {v}')

print('\n--- w/e missing IPA (sample) ---')
for b, i, t in missing_ipa_we[:30]:
    print(f'  {b}#{i}: "{t}"')

print('\n--- IPA without slashes (sample) ---')
for b, i, t, s in ipa_no_slash[:30]:
    print(f'  {b}#{i}: "{t}" ipa="{s}"')
