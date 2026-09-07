# -*- coding: utf-8 -*-
"""
收尾去重留下的合并释义：
1) 同义堆叠 / 笔误的合并项收敛为单个更通用的译法
2) 重新计算中文拼音（合并时 row[5] 还是首条释义的拼音）
3) 重新绑定中文配音，让朗读与显示文字一致（原来只念首条释义）

用法: python tools/fix_merged_zh.py [--apply]
"""
import json, os, sys, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "import_md", os.path.join(ROOT, "tools", "import_md.py"))
im = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(im)

# 合并后仍是同义堆叠或含笔误的，收敛为单个译法
SIMPLIFY = {
    "表；手表": "手表",
    "咖啡因；咖啡定": "咖啡因",          # "咖啡定" 为原文笔误
    "保留的位子；预定座位": "预定座位",
    "十字路口；路口": "十字路口",
    "刹车；刹一下车": "刹车",
    "调料；调味品": "调料",
    "书房；书斋": "书房",
}


def filled_gids():
    """从 meta.js 取已有内容的分册 gid（自动跟随新增 Parte）"""
    raw = open(os.path.join(ROOT, "data", "meta.js"), encoding="utf-8").read()
    m = json.JSONDecoder().raw_decode(raw[raw.index("=") + 1:])[0]
    out = []
    for g in m["grupos"]:
        for pt in g["partes"]:
            if sum(sc["w"] + sc["s"] + sc["e"] for sc in pt["secs"]) > 0:
                out.append(pt["gid"])
    return sorted(set(out))


def main():
    apply = "--apply" in sys.argv
    idx = im.load_audio_index() if apply else {"counter": 0, "map": {}}
    new_items, touched = [], 0
    for gid in filled_gids():
        data = im.load_sec_js(gid)
        if not data:
            continue
        changed = False
        for sec in data["secs"]:
            for kind in ("w", "e"):
                for r in sec[kind]:
                    zh = r[0] if r else ""
                    if "；" not in zh:
                        continue
                    new = SIMPLIFY.get(zh, zh)
                    touched += 1
                    print("  gid%d sec%-2d %-22r %r -> %r" % (gid, sec["no"], r[1], zh, new))
                    if apply:
                        r[0] = new
                        r[5] = im.zh_py(new)                       # 拼音跟着改
                        r[4] = im.audio_for(idx, "zh", new, new_items)  # 配音跟着改
                        changed = True
        if apply and changed:
            im.write_sec_js(gid, data)
    print("\n受影响 %d 条" % touched)
    if not apply:
        print("（dry-run，加 --apply 生效）")
        return
    im.save_audio_index(idx)
    with open(im.MANIFEST_PATH, "a", encoding="utf-8") as f:
        for x in new_items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print("待生成中文配音 %d 个（累计编号 %d）" % (len(new_items), idx["counter"]))


if __name__ == "__main__":
    main()
