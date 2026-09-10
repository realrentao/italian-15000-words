#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proper validation of data/sec/*.js files (corrected structure walker)."""
import re, json, glob, os, sys

SEC_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sec")
pattern = re.compile(r"window\.BOOK_DATA\[\d+\]=\s*(\{.*\})\s*;?\s*$", re.DOTALL)
num_prefix = re.compile(r'^\s*\d+\s+[A-Za-zàèéìòù]')

total_rows = 0
files_ok = 0
files_bad = []
num_residual = []
exact_dupes = []

for path in sorted(glob.glob(os.path.join(SEC_DIR, "*.js")), key=lambda p: int(re.search(r'(\d+)\.js$', p).group(1))):
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        s = f.read()
    m = pattern.search(s)
    if not m:
        files_bad.append((name, "no BOOK_DATA[N]= block")); continue
    try:
        obj = json.loads(m.group(1))
    except Exception as e:
        files_bad.append((name, "JSON parse fail: %s" % e)); continue
    files_ok += 1

    for sec in obj.get("secs", []):
        # word rows: row[1] is Italian
        for row in sec.get("w", []):
            if isinstance(row, list) and len(row) >= 2 and isinstance(row[1], str):
                total_rows += 1
                if num_prefix.search(row[1]):
                    num_residual.append((name, row[1][:40]))
        # sentence rows: row[0] is Italian
        for row in sec.get("s", []):
            if isinstance(row, list) and len(row) >= 1 and isinstance(row[0], str):
                total_rows += 1
                if num_prefix.search(row[0]):
                    num_residual.append((name, row[0][:40]))
        # exact-duplicate detection within w array
        seen = {}
        for i, row in enumerate(sec.get("w", [])):
            if not isinstance(row, list): continue
            key = json.dumps(row, ensure_ascii=False)
            if key in seen:
                exact_dupes.append((name, "w", seen[key], i, row[1] if len(row) > 1 else "?"))
            seen[key] = i

print("=== VALIDATION RESULT ===")
print("files parsed OK : %d" % files_ok)
print("files failed    : %d -> %s" % (len(files_bad), files_bad))
print("total rows      : %d" % total_rows)
print("leading-number residuals : %d" % len(num_residual))
for r in num_residual: print("   ", r)
print("exact-duplicate rows     : %d" % len(exact_dupes))
for d in exact_dupes: print("   ", d)
sys.exit(1 if (files_bad or num_residual or exact_dupes) else 0)
