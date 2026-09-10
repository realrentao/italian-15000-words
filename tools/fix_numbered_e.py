#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix e-rows where the Italian word field has a leading ordinal number
(e.g. "1 praticare   v.tr.") and the grammar tag was lost into the word
or left correct. Strips the number, and where 词性 was empty, splits the
trailing grammar token (v.tr./s.m./s.f./n.m./n./agg./avv.) into 词性.
Collects (it_audio_path, corrected_italian_text) for audio re-recording.
"""
import re, glob, json, os

GRAMMAR = r'(?:v\.tr\.|v\.intr\.|v\.rifl\.|s\.m\.|s\.f\.|n\.m\.|n\.|agg\.|avv\.)'
ROW = re.compile(
    r'\[\s*'
    r'"([^"]*)"'          # 0 zh
    r'\s*,\s*'
    r'"(\d+\s+[^"]*?)"'   # 1 it (starts with number)
    r'\s*,\s*'
    r'"([^"]*)"'          # 2 pos
    r'\s*,\s*'
    r'"(it/[^"]+)"'       # 3 it audio
    r'\s*,\s*'
    r'"(zh/[^"]+)"'       # 4 zh audio
    r'\s*,\s*'
    r'"([^"]*)"'          # 5 pinyin
    r'\s*,\s*'
    r'"([^"]*)"'          # 6 ipa
    r'\s*\]'
)

changes = []   # (file, zh, old_it, new_it, old_pos, new_pos, it_audio)
reco = []      # (it_audio, corrected_text)

def fix(m):
    zh, raw_it, pos, it_audio, zh_audio, pinyin, ipa = m.groups()
    it = re.sub(r'^\d+\s+', '', raw_it).strip()
    new_pos = pos
    if pos == '':
        mm = re.match(r'^(.*?)\s+(' + GRAMMAR + r')$', it)
        if mm:
            it = mm.group(1).strip()
            new_pos = mm.group(2)
    if it != raw_it or new_pos != pos:
        changes.append((zh, raw_it, it, pos, new_pos, it_audio))
        reco.append((it_audio, it))
        return (f'["{zh}","{it}","{new_pos}","{it_audio}","{zh_audio}",'
                f'"{pinyin}","{ipa}"]')
    return m.group(0)

for f in sorted(glob.glob('data/sec/1[2-5].js')):
    src = open(f, encoding='utf-8').read()
    new_src, n = ROW.subn(fix, src)
    if n:
        open(f, 'w', encoding='utf-8').write(new_src)
        print(f'{os.path.basename(f)}: {n} rows fixed')
    else:
        print(f'{os.path.basename(f)}: no change')

print(f'\nTotal fixed: {len(changes)}')
with open('tools/_reco_numbered.json', 'w', encoding='utf-8') as fh:
    json.dump(reco, fh, ensure_ascii=False, indent=1)
for zh, old, new, op, np_, au in changes:
    print(f'  {au}: "{old}" -> "{new}" (pos {op!r}->{np!r})  [{zh}]')
