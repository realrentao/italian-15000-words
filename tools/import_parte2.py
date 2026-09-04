# -*- coding: utf-8 -*-
"""
把手抄的 Parte 2（衣）原始笔记 tools/_parte2_raw.txt 导入 data/sec/1.js
格式：Section N 名称 / 终极分类词(制表符表格) / 经典意大利语句(• 列表) / 词汇大拓展(N. 列表)
词性兼容 Italian 缩写(m./f./v.pr/m.inv./inv.…) 与中文(形/名/副/动/介/连/固/短)，统一归并为 Italian 缩写。
复用 import_md 的音频去重 / 拼音 / meta 同步逻辑。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_md as im  # 需要 pypinyin（运行时用 PYTHONPATH 指向 pkgs 环境）

RAW = os.path.join(ROOT, "tools", "_parte2_raw.txt")
GID = 1
MANIFEST_PATH = os.path.join(ROOT, "audio", "_manifest.jsonl")

CJK = re.compile(u"[\u4e00-\u9fff]")

CN2IT = {"形": "adj.", "名": "n.", "副": "adv.", "动": "v.", "介": "prep.",
         "连": "cong.", "固": "loc.", "短": "loc.", "代": "pron.", "数": "num.",
         "叹": "inter."}
IT_POS = {"n", "s", "m", "f", "adj", "adv", "prep", "pron", "cong", "inter", "num",
          "art", "agg", "inv", "loc", "pl", "v", "vt", "vi", "vr", "vpr",
          "n.m", "n.f", "s.m", "s.f", "v.t", "v.i", "v.r", "v.pr", "m.inv", "f.inv"}


def norm_pos(p):
    p = (p or "").strip()
    if not p:
        return ""
    if p in CN2IT:
        return CN2IT[p]
    return p


def split_word_zh(rest):
    m = CJK.search(rest)
    if not m:
        return rest.strip(), ""
    return rest[:m.start()].strip(), rest[m.start():].strip()


def parse_sentence(line):
    text = re.sub(r"^\s*[-•·*]\s*", "", line).strip()
    if not text:
        return None
    src = ""
    m = re.search(r"——\s*[《<]([^》>]*)[》>]\s*$", text)
    if m:
        src = m.group(1).strip()
        text = text[:m.start()].strip()
    it, zh = split_word_zh(text)
    if not it or not zh:
        return None
    zh = zh.rstrip("。").strip()
    return [it, zh, src, "", "", im.zh_py(zh), ""]


def parse_expansion(line):
    """兼容两种顺序: 'it [ipa] pos. zh' 与 'zh it [ipa] pos'"""
    text = re.sub(r"^\s*\d+[.、)]\s*", "", line).strip()
    if not text:
        return None
    ipa = ""
    m = re.search(r"\[([^\]]*)\]", text)
    if m:
        ipa = m.group(1).strip()
        text = (text[:m.start()] + " " + text[m.end():]).strip()
    toks = text.split()
    pos_idx, pos = -1, ""
    for i, t in enumerate(toks):
        tt = t.rstrip(".")
        if tt in IT_POS or t in CN2IT:
            pos_idx, pos = i, t
            break
    if pos_idx < 0:  # 回退：末尾单字中文词性
        if toks and len(toks[-1]) == 1 and toks[-1] in CN2IT:
            pos_idx, pos = len(toks) - 1, toks[-1]
    if pos_idx < 0:
        return None
    before = " ".join(toks[:pos_idx]).strip()
    after = " ".join(toks[pos_idx + 1:]).strip()
    if after and CJK.search(after):          # 顺序 A: it pos. zh
        it, zh = before, after
    elif CJK.search(before):                  # 顺序 B: zh it pos
        zh, it = split_word_zh(before)
    else:
        it, zh = before, after
    it = it.strip()
    if not it:
        return None
    return [zh.strip(), it, norm_pos(pos), "", "", im.zh_py(zh.strip()), ipa]


def parse_raw(path):
    secs = []
    cur = None
    mode = None
    for raw in open(path, encoding="utf-8").read().splitlines():
        line = raw.rstrip("\n")
        m = re.match(r"^Section\s+(\d+)\s+(.*)$", line.strip())
        if m:
            cur = {"no": int(m.group(1)), "name": m.group(2).strip(),
                   "w": [], "s": [], "e": []}
            secs.append(cur)
            mode = None
            continue
        if re.match(r"^Parte\b", line.strip()):
            mode = None
            continue
        if cur is None:
            continue
        if not line.strip() or line.strip() == "---":
            continue
        if "终极分类词" in line:
            mode = "table"
            continue
        if "经典" in line:
            mode = "s"
            continue
        if "拓展" in line or "扩展" in line:
            mode = "e"
            continue
        if mode == "table":
            cells = line.split("\t") if "\t" in line else re.split(r"\s{2,}", line)
            cells = [c.strip() for c in cells]
            if len(cells) < 4:
                continue
            if cells[0] == "中文" and cells[1] == "意大利语":
                continue
            if not cells[0] or not cells[1]:
                continue
            zh, it, ipa, pos = cells[0], cells[1], cells[2], cells[3]
            ipa = ipa.strip().lstrip("[").rstrip("]").strip()
            cur["w"].append([zh, it, norm_pos(pos), "", "", im.zh_py(zh), ipa])
        elif mode == "s":
            if re.match(r"^\s*[-•·*]\s+", line):
                r = parse_sentence(line)
                if r:
                    cur["s"].append(r)
        elif mode == "e":
            if re.match(r"^\s*\d+[.、)]\s+", line):
                r = parse_expansion(line)
                if r:
                    cur["e"].append(r)
    return secs


def main():
    parsed = parse_raw(RAW)
    data = im.load_sec_js(GID)
    by_no = {x["no"]: x for x in data["secs"]}

    idx = im.load_audio_index()
    new_items = []
    for p in parsed:
        tgt = by_no.get(p["no"])
        if tgt is None:
            print("  ! 跳过 Section %d（站点无此节）" % p["no"])
            continue
        tgt["w"], tgt["s"], tgt["e"] = p["w"], p["s"], p["e"]
        for kind, f_it, f_zh in (("w", 1, 0), ("e", 1, 0), ("s", 0, 1)):
            for row in tgt[kind]:
                row[3] = im.audio_for(idx, "it", row[f_it], new_items)
                row[4] = im.audio_for(idx, "zh", row[f_zh], new_items)
        print("  Section %-2d %-16s 词%-3d 句%-2d 拓%-2d"
              % (p["no"], p["name"], len(tgt["w"]), len(tgt["s"]), len(tgt["e"])))

    im.write_sec_js(GID, data)
    im.save_audio_index(idx)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        for it in new_items:
            f.write(__import__("json").dumps(it, ensure_ascii=False) + "\n")
    total_all = im.sync_meta(GID, data)
    print("已写入 data/sec/%d.js；meta 同步（全书累计 %d 条）" % (GID, total_all))
    print("待生成音频 %d 个 → audio/_manifest.jsonl" % len(new_items))


if __name__ == "__main__":
    main()
