# -*- coding: utf-8 -*-
"""
把「生活设施 · Parte 1 在医院」Markdown 笔记 tools/_g1p1_raw.md 导入 data/sec/5.js
格式：## 终极分类词 Section N 名称 / 终极分类词(管道表格) / 经典意大利语句(N. 列表) / 词汇大拓展(N. 列表)
在 import_parte5.py 基础上增强：
  1. 词性识别改为「前缀匹配」，兼容 v.tr. / v.intr. / v.rifl. / n.m. / agg. 等任意点分缩写；
  2. 拓展行无词性时兜底按「意语 + 中文」拆分（保留 CHU: …、fare affidamento su 这类短语）。
复用 import_md 的音频去重 / 拼音 / meta 同步逻辑。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_md as im  # 需要 pypinyin

RAW = os.path.join(ROOT, "tools", "_g1p1_raw.md")
GID = 5
MANIFEST_PATH = os.path.join(ROOT, "audio", "_manifest.jsonl")

CJK = re.compile(u"[\u4e00-\u9fff]")

CN2IT = {"形": "adj.", "名": "n.", "副": "adv.", "动": "v.", "介": "prep.",
         "连": "cong.", "固": "loc.", "短": "loc.", "代": "pron.", "数": "num.",
         "叹": "inter."}
# 词性前缀：任意点分缩写都认（n.m. / v.tr. / v.intr. / v.rifl. / agg. …）
POS_PREFIX = {"n", "v", "adj", "agg", "adv", "avv", "prep", "pron", "cong",
              "inter", "int", "escl", "sost", "part", "num", "art", "loc", "inv",
              "s", "m", "f", "pl", "vt", "vi", "vr", "vpr"}


def is_pos(tok):
    t = (tok or "").strip()
    if not t:
        return False
    if t in CN2IT:
        return True
    tt = t.rstrip(".")
    return tt.split(".")[0].lower() in POS_PREFIX


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
    text = re.sub(r"^\s*\d+[\.、)\s]\s*", "", text).strip()
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
    it = it.rstrip("—").strip()
    zh = zh.rstrip("。").strip()
    return [it, zh, src, "", "", im.zh_py(zh), ""]


def parse_expansion(line):
    """兼容 'it [ipa] pos. zh'、'zh it [ipa] pos' 以及无词性的 'it zh'"""
    text = re.sub(r"^\s*\d+[\.、)\s]\s*", "", line).strip()
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
        if is_pos(t):
            pos_idx, pos = i, t
            break
    if pos_idx < 0:  # 回退：末尾单字中文词性
        if toks and len(toks[-1]) == 1 and toks[-1] in CN2IT:
            pos_idx, pos = len(toks) - 1, toks[-1]
    if pos_idx < 0:
        # 无词性兜底：按首个中文字切分意语 / 中文
        it, zh = split_word_zh(text)
        if not it or not zh:
            return None
        return [zh, it, "", "", "", im.zh_py(zh), ipa]
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
        m = re.search(r"Section\s+(\d+)\s+(.+)$", line.strip())
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
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            if cells[0] == "中文" or cells[1] in ("意大利语", "法语"):
                continue
            zh, it, ipa, pos = cells[0], cells[1], cells[2], cells[3]
            if not zh or not it:
                continue
            ipa = ipa.strip().lstrip("[").rstrip("]").strip()
            cur["w"].append([zh, it, norm_pos(pos), "", "", im.zh_py(zh), ipa])
            mode = "table"
            continue
        if mode == "s":
            if re.match(r"^\s*[-•·*]\s+", line) or re.match(r"^\s*\d+[\.、)\s]\s*", line):
                r = parse_sentence(line)
                if r:
                    cur["s"].append(r)
        elif mode == "e":
            if re.match(r"^\s*\d+[\.、)\s]\s*", line):
                r = parse_expansion(line)
                if r:
                    cur["e"].append(r)
    return secs


def main():
    parsed = [p for p in parse_raw(RAW) if (p["w"] or p["s"] or p["e"])]
    data = im.load_sec_js(GID)
    idx = im.load_audio_index()
    new_items = []
    for p in parsed:
        for kind, f_it, f_zh in (("w", 1, 0), ("e", 1, 0), ("s", 0, 1)):
            for row in p[kind]:
                row[3] = im.audio_for(idx, "it", row[f_it], new_items)
                row[4] = im.audio_for(idx, "zh", row[f_zh], new_items)
        print("  Section %-2d %-16s 词%-3d 句%-2d 拓%-2d"
              % (p["no"], p["name"], len(p["w"]), len(p["s"]), len(p["e"])))
    data["secs"] = parsed               # 整体替换，丢弃骨架空节
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
