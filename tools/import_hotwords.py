# -*- coding: utf-8 -*-
"""
把《Chapitre 社会·生活热词》简化「汉意对照热词」表导入第九大篇「社会·生活热词」
（gid 49，单一 Parte「时尚热词」，12 个 Section）。

文档特点：每行只有 中文 + 意大利语 两列，无词性 / 音标 / 例句 / 拓展。
Section 1 为两行一配对，Section 2–12 为「中文意大利语擦边球azione…」整段拼接，
故用 CJK / Latin 游程切分稳健拆分，建模为 w 行 [zh, it, "", it_mp3, zh_mp3, 拼音, ""]。
"""
import os
import re
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_md import (load_audio_index, save_audio_index, audio_for,
                       write_sec_js, zh_py, MANIFEST_PATH, ROOT)

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ch9_raw.md")
GID = 49
GNAME = "社会·生活热词"
PNAME = "时尚热词"


def extract_pairs(text):
    """从一段 Section 文本中拆出 (中文, 意大利语) 配对。"""
    text = text.replace("中文意大利语", "")  # 去掉拼接表头
    runs = []
    for m in re.finditer(r"([\u4e00-\u9fff]+)|([^\u4e00-\u9fff]+)", text):
        if m.group(1):
            c = m.group(1)
            if c.startswith("中文意大利语"):
                c = c[len("中文意大利语"):]
            c = c.strip()
            if c in ("中文", "意大利语", ""):
                continue
            runs.append(("cjk", c))
        else:
            lat = m.group(2).strip()
            if not lat:
                continue
            runs.append(("lat", lat))
    pairs = []
    i = 0
    while i + 1 < len(runs):
        if runs[i][0] == "cjk" and runs[i + 1][0] == "lat":
            pairs.append((runs[i][1], runs[i + 1][1]))
            i += 2
        else:
            i += 1
    return pairs


def parse_md_hot(src):
    with open(src, encoding="utf-8") as f:
        lines = f.read().splitlines()
    secs = []
    cur = None
    buf = []
    for raw in lines:
        m = re.match(r"^\s*Section\s*(\d+)\s*(.*)$", raw)
        if m:
            if cur is not None:
                cur["pairs"] = extract_pairs("\n".join(buf))
                secs.append(cur)
            cur = {"no": int(m.group(1)),
                   "name": re.sub(r"（页[^）]*）", "", m.group(2)).strip() or m.group(2).strip(),
                   "buf": []}
            buf = []
            continue
        if cur is None:
            continue
        buf.append(raw)
    if cur is not None:
        cur["pairs"] = extract_pairs("\n".join(buf))
        secs.append(cur)
    return secs


def update_meta(data_secs):
    p = os.path.join(ROOT, "data", "meta.js")
    s = open(p, encoding="utf-8").read()
    meta = json.JSONDecoder().raw_decode(s[s.index("=") + 1:])[0]
    parte = {"gid": GID, "no": 1, "name": PNAME, "secs": [
        {"no": sc["no"], "name": sc["name"], "w": len(sc["w"]), "s": 0, "e": 0}
        for sc in data_secs]}
    meta["grupos"].append({"name": GNAME, "partes": [parte]})
    meta["totalAll"] = sum(
        sc["w"] + sc["s"] + sc["e"]
        for g in meta["grupos"] for pt in g["partes"] for sc in pt["secs"])
    body = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    open(p, "w", encoding="utf-8").write("window.BOOK_META=%s;\n" % body)
    return meta["totalAll"]


def build():
    secs = parse_md_hot(SRC)
    idx = load_audio_index()
    new_items = []
    data_secs = []
    total_w = 0
    for sc in secs:
        w = []
        for zh, it in sc["pairs"]:
            zh, it = zh.strip(), it.strip()
            if not zh or not it:
                continue
            row = [zh, it, "", "", "", zh_py(zh), ""]
            row[3] = audio_for(idx, "it", it, new_items)
            row[4] = audio_for(idx, "zh", zh, new_items)
            w.append(row)
            total_w += 1
        data_secs.append({"no": sc["no"], "name": sc["name"], "w": w, "s": [], "e": []})
    data = {"gid": GID, "no": 1, "name": PNAME, "gname": GNAME, "secs": data_secs}
    write_sec_js(GID, data)
    save_audio_index(idx)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        for it in new_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    total_all = update_meta(data_secs)
    return total_w, len(new_items), total_all, data_secs


def summary():
    secs = parse_md_hot(SRC)
    tot = 0
    print("Partie 时尚热词 → 12 Section，解析配对预览：")
    for sc in secs:
        tot += len(sc["pairs"])
        print("  Section %-2d %-14s 词 %-3d  样例: %s → %s"
              % (sc["no"], sc["name"], len(sc["pairs"]),
                 sc["pairs"][0][0] if sc["pairs"] else "-",
                 sc["pairs"][0][1] if sc["pairs"] else "-"))
    print("合计 %d 条（全部为 w 行，无 s/e）" % tot)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        summary()
    else:
        tw, na, ta, _ = build()
        print("已写入 data/sec/%d.js（gname=%s, parte=%s）" % (GID, GNAME, PNAME))
        print("w 行 %d 条；待生成音频 %d 个；meta totalAll=%d" % (tw, na, ta))
