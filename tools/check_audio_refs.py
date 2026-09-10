#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify every audio path referenced in data/sec/*.js exists on disk."""
import re, json, glob, os, sys

SEC_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sec")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "audio")
pattern = re.compile(r"window\.BOOK_DATA\[\d+\]=\s*(\{.*\})\s*;?\s*$", re.DOTALL)

missing = []
checked = 0
for path in sorted(glob.glob(os.path.join(SEC_DIR, "*.js")), key=lambda p: int(re.search(r'(\d+)\.js$', p).group(1))):
    with open(path, encoding="utf-8") as f:
        obj = json.loads(pattern.search(f.read()).group(1))
    for sec in obj.get("secs", []):
        for row in sec.get("w", []) + sec.get("s", []):
            if not isinstance(row, list): continue
            for cell in row:
                if isinstance(cell, str) and re.match(r'^(it|zh)/\d+\.mp3$', cell):
                    checked += 1
                    if not os.path.exists(os.path.join(AUDIO_DIR, cell)):
                        missing.append(cell)

print("audio refs checked : %d" % checked)
print("missing on disk    : %d" % len(missing))
for m in sorted(set(missing)): print("   MISSING", m)
sys.exit(1 if missing else 0)
