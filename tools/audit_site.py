#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full QA audit of the vocab site data files."""
import glob, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[一-鿿]')
ROW = re.compile(
    r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
    r'"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
)

missing_it = []; missing_zh = []
audio_collision = defaultdict(list)   # file -> list of (file, text)
empty_pos_we = []
empty_it = []
empty_zh = []
rowcount = 0

for f in sorted(glob.glob(os.path.join(ROOT, 'data/sec/*.js'))):
    src = open(f, encoding='utf-8').read()
    base = os.path.basename(f)
    for m in ROW.finditer(src):
        g = m.groups()
        rowcount += 1
        f0, f1, f2, it_a, zh_a, py, ipa = g
        # decide Italian text field
        it_text = f1 if CJK.search(f0) else f0   # w/e: f1; s: f0
        zh_text = f0 if CJK.search(f0) else f1
        kind = 'we' if CJK.search(f0) else 's'
        if kind == 'we' and not f2.strip():
            empty_pos_we.append((base, it_text))
        if not it_text.strip():
            empty_it.append((base,))
        if not zh_text.strip():
            empty_zh.append((base,))
        # audio existence
        if it_a:
            p = os.path.join(ROOT, 'audio', it_a)
            if not os.path.isfile(p):
                missing_it.append((base, it_a, it_text))
            else:
                audio_collision[it_a].append((base, it_text))
        if zh_a:
            p = os.path.join(ROOT, 'audio', zh_a)
            if not os.path.isfile(p):
                missing_zh.append((base, zh_a, zh_text))
            else:
                audio_collision[zh_a].append((base, zh_text))

# collisions: same audio file used for >1 distinct text
collisions = {k: v for k, v in audio_collision.items() if len(set(t for _, t in v)) > 1}

print(f'Total rows parsed     : {rowcount}')
print(f'Missing IT audio files: {len(missing_it)}')
print(f'Missing ZH audio files: {len(missing_zh)}')
print(f'w/e rows empty 词性   : {len(empty_pos_we)}')
print(f'Rows empty 意语       : {len(empty_it)}')
print(f'Rows empty 中文       : {len(empty_zh)}')
print(f'Audio-file collisions : {len(collisions)} (same file, >1 distinct text)')

print('\n--- Missing IT audio ---')
for b, a, t in missing_it[:40]: print(f'  {b}: {a}  ("{t}")')
print('--- Missing ZH audio ---')
for b, a, t in missing_zh[:40]: print(f'  {b}: {a}  ("{t}")')
print('--- w/e empty 词性 (sample) ---')
for b, t in empty_pos_we[:40]: print(f'  {b}: "{t}"')
print('--- collisions (sample) ---')
for k, v in list(collisions.items())[:20]:
    print(f'  {k}: {sorted(set(v))}')
