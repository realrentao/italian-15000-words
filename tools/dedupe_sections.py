# -*- coding: utf-8 -*-
"""
同节内去重：以「意大利语词形」为键，每个 Section 内只保留一条。
- 完全相同的行 -> 直接删除
- 同词不同中文释义 -> 合并中文（用 ；连接），不丢含义
- 跨 w/e（终极分类词 vs 词汇大拓展）同词 -> 并入 w，删除 e 中的冗余项
不改动 s（经典句）。音频沿用首条，不重新生成。
"""
import json, os, re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_sec_js(gid):
    p = os.path.join(ROOT, "data", "sec", "%d.js" % gid)
    with open(p, encoding="utf-8") as f:
        s = f.read()
    return json.JSONDecoder().raw_decode(s[s.index("{", s.index("BOOK_DATA[")):])[0]

def write_sec_js(gid, data):
    p = os.path.join(ROOT, "data", "sec", "%d.js" % gid)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(p, "w", encoding="utf-8") as f:
        f.write("window.BOOK_DATA=window.BOOK_DATA||{};window.BOOK_DATA[%d]=%s;\n" % (gid, body))

def norm(it):
    if not it:
        return ""
    x = it.strip().lower()
    x = re.sub(r"[.,;:!?()\[\]'\"\s]+", "", x)
    return x

def dedupe_sec(sec):
    """返回 (new_w, new_e, changes)。changes 为可读改动列表。"""
    changes = []
    merged = OrderedDict()
    for kind in ("w", "e"):
        for i, row in enumerate(sec[kind]):
            it = row[1] if len(row) > 1 else ""
            if not it:
                continue
            n = norm(it)
            zh = row[0] if row else ""
            if n not in merged:
                merged[n] = {
                    "it": it, "zh": zh, "zhset": {zh} if zh else set(),
                    "pos": row[2] if len(row) > 2 else "",
                    "itmp3": row[3], "zhmp3": row[4],
                    "py": row[5] if len(row) > 5 else "",
                    "ipa": row[6] if len(row) > 6 else "",
                    "kinds": set([kind]), "worder": i if kind == "w" else None,
                    "eorder": i if kind == "e" else None,
                    "first": "%s#%d" % (kind, i),
                }
            else:
                m = merged[n]
                was = m["zh"]
                m["kinds"].add(kind)
                if zh and zh not in m["zhset"]:
                    m["zhset"].add(zh)
                    m["zh"] = (m["zh"] + "；" + zh) if m["zh"] else zh
                    changes.append("合并 %s 的「%s」<- 原 %s「%s」" % (n, was, "%s#%d" % (kind, i), zh))
                else:
                    changes.append("删除重复 %s（%s「%s」与首条相同）" % (n, kind, zh))
                if kind == "w" and m["worder"] is None:
                    m["worder"] = i
                if kind == "e" and m["eorder"] is None:
                    m["eorder"] = i
                if not m["pos"] and len(row) > 2 and row[2]:
                    m["pos"] = row[2]
                if not m["ipa"] and len(row) > 6 and row[6]:
                    m["ipa"] = row[6]
    new_w, new_e = [], []
    for n, m in merged.items():
        row = [m["zh"], m["it"], m["pos"], m["itmp3"], m["zhmp3"], m["py"], m["ipa"]]
        if "w" in m["kinds"]:
            new_w.append((m["worder"] if m["worder"] is not None else 999, row))
        else:
            new_e.append((m["eorder"], row))
    new_w.sort(key=lambda x: x[0])
    new_e.sort(key=lambda x: x[0])
    return [r for _, r in new_w], [r for _, r in new_e], changes

def main():
    log_lines = []
    grand_removed = 0
    for gid in range(0, 5):
        data = load_sec_js(gid)
        if not data:
            continue
        for sec in data["secs"]:
            before_w, before_e = len(sec["w"]), len(sec["e"])
            nw, ne, chgs = dedupe_sec(sec)
            after_w, after_e = len(nw), len(ne)
            removed = (before_w + before_e) - (after_w + after_e)
            if removed or chgs:
                grand_removed += removed
                head = "Parte gid=%d  Section %d %s  (词 %d->%d, 拓 %d->%d, 删 %d)" % (
                    gid, sec["no"], sec.get("name", ""), before_w, after_w, before_e, after_e, removed)
                log_lines.append(head)
                for c in chgs:
                    log_lines.append("    " + c)
            sec["w"], sec["e"] = nw, ne
        write_sec_js(gid, data)
    log = "\n".join(log_lines)
    print(log)
    print("\n全站合计删除冗余行: %d" % grand_removed)
    # 同步 meta 统计
    sys_path = os.path.join(ROOT, "tools", "import_md.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("import_md", sys_path)
    im = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(im)
    for gid in range(0, 5):
        data = load_sec_js(gid)
        im.sync_meta(gid, data)
    print("已同步 data/meta.js 统计。")

if __name__ == "__main__":
    main()
