# -*- coding: utf-8 -*-
"""
为「阳性,阴性」合写词条（如 "privato, a"）补充阴性形态音频与文本。

数据层：w/e 行原 7 字段 [zh,it,pos,it_mp3,zh_mp3,py,ipa]，
         app.js 已读取 it[7](阴性音频) / it[8](阴性文本) 实现「阳→阴」连播。
         本脚本把阴性派生词填入 it[7]/it[8]，并按文本去重生成阴性意语音频。

派生规则：
  - 尾 "a"      : masc[:-1] + 'a'   (privato -> privata)
  - 尾 "trice"  : masc[:-3] + 'rice' (direttore -> direttrice)
  - 尾 "una"    : 'una'             (uno -> una)
  - 兜底        : masc[:-1] + tail

用法：
  python tools/add_feminine.py --dry     # 仅打印将生成的阴性词，不改任何文件
  python tools/add_feminine.py --go      # 实际写入 sec 文件 + 索引 + manifest
"""
import json, glob, re, sys, os, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import tools.import_md as im

PAT = re.compile(r'^\s*([^,]+?)\s*,\s*([A-Za-zàèéìíîòóùúüç\'\-]+)\s*$', re.I)
SEC_DIR = os.path.join(im.ROOT, "data", "sec")


def derive_fem(masc, tail):
    m = masc.strip()
    t = tail.strip().lower()
    if not m:
        return ""
    if t == "a":
        return m[:-1] + "a"
    if t == "trice":
        return m[:-3] + "rice"
    if t == "una":
        return "una"
    return m[:-1] + tail


def iter_sec():
    for p in sorted(glob.glob(os.path.join(SEC_DIR, "*.js"))):
        s = open(p, encoding="utf-8").read()
        start = s.index("{", s.index("BOOK_DATA["))
        obj = json.JSONDecoder().raw_decode(s[start:])[0]
        yield p, obj


def fix_counter(idx):
    """把 counter 提升到「磁盘已有 mp3 最大编号 + 1」，避免与历史音频撞号覆盖。"""
    mx = idx.get("counter", 0)
    for lang in ("it", "zh"):
        d = os.path.join(im.AUDIO_DIR, lang)
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.endswith(".mp3"):
                try:
                    n = int(fn[:-4])
                    if n >= mx:
                        mx = n + 1
                except ValueError:
                    pass
    idx["counter"] = mx
    return mx


def main():
    mode = "--go" if "--go" in sys.argv else "--dry"
    idx = im.load_audio_index()
    if mode == "--go":
        fix_counter(idx)
    new_items = []
    rows = []          # (file, kind, orig, fem, already)
    changed_gids = set()

    # 单遍：解析 -> 改内存 -> 同步写回同一文件（避免二次读取覆盖）
    for p, obj in iter_sec():
        gid = obj.get("gid")
        changed = False
        for sc in obj["secs"]:
            for kind in ("w", "e"):
                for row in sc.get(kind, []):
                    if len(row) < 7:
                        continue
                    it = row[1] if len(row) > 1 else ""
                    m = PAT.match(it.strip())
                    if not m:
                        continue
                    masc, tail = m.group(1).strip(), m.group(2).strip()
                    fem = derive_fem(masc, tail)
                    already = len(row) > 8 and (row[7] or row[8])
                    rows.append((p.split("/")[-1], kind, it.strip(), fem, already))
                    if mode == "--go" and fem and not already:
                        while len(row) < 9:
                            row.append("")
                        row[7] = im.audio_for(idx, "it", fem, new_items)
                        row[8] = fem
                        changed = True
                        changed_gids.add(gid)
        if mode == "--go" and changed:
            im.write_sec_js(gid, obj)

    if mode == "--dry":
        out = ["=== DRY: 将生成的阴性派生词（共 %d）===" % len(rows)]
        for f, kind, orig, fem, already in rows:
            warn = "" if (fem.endswith("a") or fem.endswith("e")) else "  <-- 检查"
            out.append("  %-12s %s  %-22s -> %-18s %s%s" %
                       (f, kind, orig, fem, "已填" if already else "", warn))
        open(os.path.join(im.ROOT, "tools", "_add_fem_dry.txt"), "w", encoding="utf-8").write("\n".join(out))
        print("DRY 共扫描到 %d 个「A,B」词条，写入 tools/_add_fem_dry.txt" % len(rows))
        return

    # --go
    im.save_audio_index(idx)
    with open(im.MANIFEST_PATH, "a", encoding="utf-8") as f:
        for it in new_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    out = ["=== GO: 已处理 %d 个 gid，新增阴性音频 %d 个 ===" % (len(changed_gids), len(new_items))]
    out.append("索引 counter 现: %d" % idx["counter"])
    for f, kind, orig, fem, already in rows:
        if not already:
            out.append("  %-12s %s  %-22s -> %-18s" % (f, kind, orig, fem))
    open(os.path.join(im.ROOT, "tools", "_add_fem_go.txt"), "w", encoding="utf-8").write("\n".join(out))
    print("GO 完成：改动 %d 个分册，新增阴性音频 %d 个，详见 tools/_add_fem_go.txt" %
          (len(changed_gids), len(new_items)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(os.path.join(ROOT, "tools", "_add_fem_err.txt"), "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
