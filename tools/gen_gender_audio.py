# -*- coding: utf-8 -*-
"""
为「阳性/阴性合写」词条（如 nono, a / stretto, a / uno, una）分别配音。

规则：
  it[3] -> 阳性（或原形）单独配音（原来是把 "nono, a" 整串拿去念）
  it[7] -> 阴性形态单独配音（新增字段）
  it[8] -> 阴性形态文本（新增字段，用于 UI 显示）

用法:
  python tools/gen_gender_audio.py          # dry-run，只打印
  python tools/gen_gender_audio.py --apply  # 写入并登记待生成音频
"""
import json, os, re, sys, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_im_path = os.path.join(ROOT, "tools", "import_md.py")
_spec = importlib.util.spec_from_file_location("import_md", _im_path)
im = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(im)

# "nono, a" / "nono, -a" / "nono/a"
PAT_C = re.compile(r"^([A-Za-zÀ-ÿ'’]+)\s*,\s*(-?[A-Za-zÀ-ÿ]{1,6})$")
PAT_S = re.compile(r"^([A-Za-zÀ-ÿ'’]+)\s*/\s*([A-Za-zÀ-ÿ]{1,6})$")


def expand_forms(it):
    """'nono, a' -> ('nono','nona')；'uno, una' -> ('uno','una')；不匹配返回 None"""
    if not it:
        return None
    s = it.strip()
    m = PAT_C.match(s) or PAT_S.match(s)
    if not m:
        return None
    base, suf = m.group(1), m.group(2).lstrip("-")
    if not base or not suf:
        return None
    # 只接受阴性词尾（a / e / he 等），避免误伤 "ristorante, bar" 之类并列
    if suf.lower() not in ("a", "e", "una", "essa", "trice", "rice", "ina", "ona"):
        return None
    if len(suf) > 1:
        fem = suf                      # 给出了完整阴性形，如 uno, una
    elif base.endswith("o"):
        fem = base[:-1] + suf          # nono -> nona
    elif base.endswith("e"):
        fem = base                     # -e 结尾形容词单数为通性，如 grande
    else:
        fem = base + suf
    if not fem or fem == base and len(suf) > 1 and suf != base:
        pass
    return base, fem


def main():
    apply = "--apply" in sys.argv
    idx = im.load_audio_index() if apply else {"counter": 0, "map": {}}
    new_items = []
    total = 0
    rows = []
    for gid in range(0, 5):
        data = im.load_sec_js(gid)
        if not data:
            continue
        for sec in data["secs"]:
            for kind in ("w", "e"):
                for i, r in enumerate(sec[kind]):
                    it = r[1] if len(r) > 1 else ""
                    ex = expand_forms(it)
                    if not ex:
                        continue
                    base, fem = ex
                    total += 1
                    rows.append("  gid%d sec%-2d %-14s [%s#%d] %-22r -> %r / %r  (%s)" % (
                        gid, sec["no"], sec.get("name", ""), kind, i, it, base, fem,
                        r[0] if r else ""))
                    if apply:
                        r[3] = im.audio_for(idx, "it", base, new_items)
                        while len(r) < 7:
                            r.append("")
                        r.append(im.audio_for(idx, "it", fem, new_items))
                        r.append(fem)
        if apply:
            im.write_sec_js(gid, data)
    print("\n".join(rows))
    print("\n共 %d 条阴阳合写词条" % total)
    if not apply:
        print("（dry-run，未写入；加 --apply 生效）")
        return
    im.save_audio_index(idx)
    with open(im.MANIFEST_PATH, "a", encoding="utf-8") as f:
        for x in new_items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print("已写入 data/sec/*.js；待生成音频 %d 个（累计编号 %d）" % (len(new_items), idx["counter"]))


if __name__ == "__main__":
    main()
