# -*- coding: utf-8 -*-
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_sec_js(gid):
    p = os.path.join(ROOT, "data", "sec", "%d.js" % gid)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        s = f.read()
    return json.JSONDecoder().raw_decode(s[s.index("{", s.index("BOOK_DATA[")):])[0]

def norm(it):
    if not it:
        return ""
    x = it.strip().lower()
    x = re.sub(r"[.,;:!?()\[\]'\"\s]+", "", x)
    return x

def main():
    total_dup_rows = 0
    for gid in range(0, 5):  # 已填充的 Parte 0-4
        data = load_sec_js(gid)
        if not data:
            continue
        for sec in data["secs"]:
            # 收集 w/e 的意大利语词（index 1）
            pool = []  # (norm, kind, idx_in_list, row)
            for kind in ("w", "e"):
                for i, row in enumerate(sec[kind]):
                    it = row[1] if row and len(row) > 1 else ""
                    if it:
                        pool.append((norm(it), kind, i, row))
            # 找重复
            from collections import defaultdict
            d = defaultdict(list)
            for key, kind, i, row in pool:
                if key:
                    d[key].append((kind, i, row))
            dups = {k: v for k, v in d.items() if len(v) > 1}
            if dups:
                print("\n=== Parte gid=%d  Section %d %s ===" % (gid, sec["no"], sec.get("name", "")))
                for k, v in dups.items():
                    total_dup_rows += len(v) - 1
                    print("  重复键 %r :" % k)
                    for kind, i, row in v:
                        it = row[1] if len(row) > 1 else ""
                        zh = row[0] if row else ""
                        print("    [%s#%d] %s | %s" % (kind, i, it, zh))
    print("\n全站(Parte0-4) 同节内重复词导致的冗余行数: %d" % total_dup_rows)

if __name__ == "__main__":
    main()
