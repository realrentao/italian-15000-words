# -*- coding: utf-8 -*-
"""
把《意语单词随身背》Markdown 笔记导入学习站 data/sec/<gid>.js

用法:
  python tools/import_md.py <md文件路径> <gid> [--audio]

数据格式（与 js/app.js 的 block / blockSent 对应）:
  w (终极分类词) : [zh, it, pos, it_mp3, zh_mp3, py, ipa]
  e (词汇大拓展) : [zh, it, pos, it_mp3, zh_mp3, py, ipa]
  s (经典实用句) : [it, zh, src, it_mp3, zh_mp3, py, ipa]

音频编号: audio/<lang>/<NNNNN>.mp3，全局自增计数器 + 文本去重，
        缓存文件 audio/_index.json，可反复运行、跨分册续编。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(ROOT, "audio")
INDEX_PATH = os.path.join(AUDIO_DIR, "_index.json")
MANIFEST_PATH = os.path.join(AUDIO_DIR, "_manifest.jsonl")

CJK = re.compile(u"[\u4e00-\u9fff]")
# 词性标记（词汇大拓展里的顺序不固定，需要识别后剔除）
POS_RE = re.compile(
    r"\b(n\.m\.|n\.f\.|v\.t\.|v\.i\.|v\.r\.|adj\.|adv\.|prep\.|pron\.|cong\.|"
    r"inter\.|num\.|art\.|agg\.|s\.m\.|s\.f\.|m\.inv|f\.inv|inv\.|pl\.)",
    re.I,
)


# ---------------- 音频 ----------------
def load_audio_index():
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"counter": 0, "map": {}}


def save_audio_index(idx):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)


def audio_for(idx, lang, text, new_items):
    """返回 audio/<lang>/NNNNN.mp3；新文本分配新编号并写入 manifest。"""
    if not text:
        return ""
    key = lang + "|" + text
    hit = idx["map"].get(key)
    if hit is not None:
        return hit
    n = idx["counter"]
    idx["counter"] += 1
    rel = "%s/%05d.mp3" % (lang, n)
    idx["map"][key] = rel
    new_items.append({"lang": lang, "text": text, "file": rel})
    return rel


# ---------------- Markdown 解析 ----------------
def split_word_zh(rest):
    """从 'bosco 森林，树林' / 'numeroso, a 众多的' 拆出 (外文, 中文)"""
    m = CJK.search(rest)
    if not m:
        return rest.strip(), ""
    return rest[:m.start()].strip(), rest[m.start():].strip()


def parse_expansion(line):
    """词汇大拓展: '1. numeroso, a [nuˈmɛrɔzo] adj. 众多的，许多的'"""
    text = re.sub(r"^\s*\d+[.、)]\s*", "", line).strip()
    if not text:
        return None
    ipa = ""
    m = re.search(r"\[([^\]]*)\]", text)
    if m:
        ipa = m.group(1).strip()
        text = (text[:m.start()] + " " + text[m.end():]).strip()
    pos = ""
    m = POS_RE.search(text)
    if m:
        pos = m.group(1)
        text = (text[:m.start()] + " " + text[m.end():]).strip()
    it, zh = split_word_zh(text)
    if not it:
        return None
    return [zh, it, pos, "", "", "", ipa]


def parse_sentence(line):
    """经典句: '- Il coraggio ... fattori vitali. 勇气和快乐……。——《绝望的主妇》'"""
    text = re.sub(r"^\s*[-*]\s*", "", line).strip()
    if not text:
        return None
    src = ""
    m = re.search(u"——\s*[《<]([^》>]*)[》>]\s*$", text)
    if m:
        src = m.group(1).strip()
        text = text[:m.start()].strip()
    it, zh = split_word_zh(text)
    if not it or not zh:
        return None
    zh = zh.rstrip("。").strip()
    return [it, zh, src, "", "", "", ""]


def parse_md(path):
    """返回 [(sec_no, sec_name, w, s, e), ...]"""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    secs = []
    cur = None
    mode = None  # 'table' | 's' | 'e'
    for raw in lines:
        line = raw.rstrip()
        m = re.match(r"^#{2,4}\s*Section\s*(\d+)\s*(.*)$", line, re.I)
        if m:
            cur = {"no": int(m.group(1)), "name": m.group(2).strip(),
                   "w": [], "s": [], "e": []}
            secs.append(cur)
            mode = None
            continue
        if re.match(r"^#{2,4}\s*Parte\b", line, re.I):
            mode = None
            continue
        if cur is None:
            continue

        if line.startswith("|"):
            mode = "table"
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            if cells[0] in (u"中文", "") and cells[1] == u"意大利语":
                continue
            zh, it, ipa, pos = cells[0], cells[1], cells[2], cells[3]
            if not it or not zh:
                continue
            ipa = ipa.strip().lstrip("[").rstrip("]").strip()
            cur["w"].append([zh, it, pos, "", "", "", ipa])
            continue

        if line.startswith("**") and line.rstrip().endswith("**"):
            head = line.strip("*").strip()
            mode = "table" if u"终极分类词" in head else (
                "s" if u"经典" in head else ("e" if u"拓展" in head or u"扩展" in head else None))
            continue

        if not line.strip() or line.strip() == "---":
            continue

        if mode == "s" and re.match(r"^\s*[-*]\s+", line):
            r = parse_sentence(line)
            if r:
                cur["s"].append(r)
        elif mode == "e" and re.match(r"^\s*\d+[.、)]\s+", line):
            r = parse_expansion(line)
            if r:
                cur["e"].append(r)
    return secs


# ---------------- 写入 ----------------
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


def sync_meta(gid, data):
    """把 data/sec/<gid>.js 的统计同步回 data/meta.js"""
    p = os.path.join(ROOT, "data", "meta.js")
    with open(p, encoding="utf-8") as f:
        s = f.read()
    meta = json.JSONDecoder().raw_decode(s[s.index("=") + 1:])[0]
    stat = {x["no"]: (len(x["w"]), len(x["s"]), len(x["e"])) for x in data["secs"]}
    for g in meta["grupos"]:
        for pt in g["partes"]:
            if pt["gid"] != gid:
                continue
            for sc in pt["secs"]:
                if sc["no"] in stat:
                    sc["w"], sc["s"], sc["e"] = stat[sc["no"]]
    meta["totalAll"] = sum(
        sc["w"] + sc["s"] + sc["e"]
        for g in meta["grupos"] for pt in g["partes"] for sc in pt["secs"])
    body = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    with open(p, "w", encoding="utf-8") as f:
        f.write("window.BOOK_META=%s;\n" % body)
    return meta["totalAll"]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    md, gid = sys.argv[1], int(sys.argv[2])
    want_audio = "--audio" in sys.argv

    parsed = parse_md(md)
    data = load_sec_js(gid)
    by_no = {x["no"]: x for x in data["secs"]}

    idx = load_audio_index()
    new_items = []
    total = 0
    for p in parsed:
        tgt = by_no.get(p["no"])
        if tgt is None:
            print("  ! 跳过 Section %d（站点 Parte %d 无此节）" % (p["no"], gid))
            continue
        tgt["w"] = p["w"]
        tgt["s"] = p["s"]
        tgt["e"] = p["e"]
        for kind, fld_it, fld_zh in (("w", 1, 0), ("e", 1, 0), ("s", 0, 1)):
            for row in tgt[kind]:
                row[3] = audio_for(idx, "it", row[fld_it], new_items)
                row[4] = audio_for(idx, "zh", row[fld_zh], new_items)
                total += 1
        print("  Section %-2d %-16s 词%-3d 句%-2d 拓%-2d"
              % (p["no"], p["name"], len(tgt["w"]), len(tgt["s"]), len(tgt["e"])))

    write_sec_js(gid, data)
    save_audio_index(idx)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        for it in new_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    total_all = sync_meta(gid, data)

    print("已写入 data/sec/%d.js；meta 统计已同步（全书累计 %d 条）" % (gid, total_all))
    print("待生成音频 %d 个（累计编号 %d）→ 记录于 audio/_manifest.jsonl"
          % (len(new_items), idx["counter"]))
    if want_audio:
        os.system('"%s" "%s"' % (sys.executable,
                                 os.path.join(ROOT, "tools", "gen_audio.py")))


if __name__ == "__main__":
    main()
