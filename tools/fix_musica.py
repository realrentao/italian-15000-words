#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix the Music Festival sentence (Parte 1 · Sec 10):
   - detach stray ' 6' from Italian -> correct Italian
   - Chinese '月21日' -> '6月21日'
   - pinyin 'yuè 21 rì' -> 'liù yuè 21 rì'
   Regenerate it/00581.mp3 + zh/00582.mp3 and update audio cache keys.
"""
import json, re, asyncio, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC0 = os.path.join(ROOT, "data", "sec", "0.js")
IDX  = os.path.join(ROOT, "audio", "_index.json")

OLD_IT = "Il 21 giugno è la Festa della Musica, è una festa nuova che esiste dal 1982. 6"
NEW_IT = "Il 21 giugno è la Festa della Musica, è una festa nuova che esiste dal 1982."
OLD_ZH = "月21日是音乐节，这是1982年设立的一个节日"
NEW_ZH = "6月21日是音乐节，这是1982年设立的一个节日"
OLD_PY = "yuè 21 rì shì yīn yuè jié，zhè shì 1982 nián shè lì de yí gè jié rì"
NEW_PY = "liù yuè 21 rì shì yīn yuè jié，zhè shì 1982 nián shè lì de yí gè jié rì"

# ---- 1. patch data file (exact substring replacement, format-preserving) ----
s = open(SEC0, encoding="utf-8").read()
assert s.count(OLD_IT) == 1, f"OLD_IT count={s.count(OLD_IT)}"
assert s.count(OLD_ZH) == 1, f"OLD_ZH count={s.count(OLD_ZH)}"
assert s.count(OLD_PY) == 1, f"OLD_PY count={s.count(OLD_PY)}"
s = s.replace(OLD_IT, NEW_IT).replace(OLD_ZH, NEW_ZH).replace(OLD_PY, NEW_PY)
open(SEC0, "w", encoding="utf-8").write(s)
print("[data] patched 0.js")

# ---- 2. regenerate audio ----
import edge_tts

async def synth(text, voice, out):
    comm = edge_tts.Communicate(text=text, voice=voice)
    await comm.save(out)
    print(f"[audio] {out}  ({voice})  bytes={os.path.getsize(out)}")

async def main():
    await synth(NEW_IT, "it-IT-ElsaNeural", os.path.join(ROOT, "audio", "it", "00581.mp3"))
    await synth(NEW_ZH, "zh-CN-XiaoxiaoNeural", os.path.join(ROOT, "audio", "zh", "00582.mp3"))

asyncio.run(main())

# ---- 3. update audio cache keys ----
idx = json.load(open(IDX, encoding="utf-8"))
m = idx["map"]
old_it_key = "it|" + OLD_IT
old_zh_key = "zh|" + OLD_ZH
assert old_it_key in m and m[old_it_key] == "it/00581.mp3", "it key mismatch"
assert old_zh_key in m and m[old_zh_key] == "zh/00582.mp3", "zh key mismatch"
m["it|" + NEW_IT] = "it/00581.mp3"
m["zh|" + NEW_ZH] = "zh/00582.mp3"
del m[old_it_key]
del m[old_zh_key]
json.dump(idx, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[cache] updated _index.json keys")
print("DONE")
