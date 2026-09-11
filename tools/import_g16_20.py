# -*- coding: utf-8 -*-
"""
导入 Chapitre 4 校园 / Partie 1–5 -> gid 16..20
源: tools/_ch4_campus_raw.md
格式:
  - 词表为制表符分隔的 4 列: 中文(含词性前缀) \t 意大利语 \t [音标] \t 词性
  - 经典句: • 意大利语. 中文翻译。——《出处》
  - 拓展:   1 意语 [ipa] pos. 中文
复用 import_md 的 audio_for / write_sec_js / save_audio_index / sync_meta / zh_py /
            parse_sentence / parse_expansion
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_md as im  # noqa

RAW = os.path.join(ROOT, "tools", "_ch4_campus_raw.md")
PARTE2GID = {1: 16, 2: 17, 3: 18, 4: 19, 5: 20}

CJK = re.compile(r"[\u4e00-\u9fff]")
POSPRE = re.compile(r"^(名|形|动|副|介|连|固|短|代|数|叹|量)\s+")

# 补全词性识别（import_md 默认 POS_RE 缺 avv./v.pr. 等）
im.POS_RE = re.compile(
    r"\b(n\.m\.|n\.f\.|v\.t\.|v\.i\.|v\.r\.|v\.pr\.|adj\.|adv\.|avv\.|prep\.|"
    r"pron\.|cong\.|inter\.|num\.|art\.|agg\.|s\.m\.|s\.f\.|m\.inv|f\.inv|inv\.|"
    r"pl\.|loc\.)", re.I)


def mk_w(zh_raw, it, ipa, pos):
    """构造 w / e 行 7 字段 [zh, it, pos, it_mp3, zh_mp3, py, ipa]"""
    zh = POSPRE.sub("", zh_raw).strip()
    it = (it or "").strip()
    if not zh or not it:
        return None
    ipa = (ipa or "").strip().lstrip("[").rstrip("]").strip()
    pos = (pos or "").strip()
    return [zh, it, pos, "", "", im.zh_py(zh), ipa]


def parse_raw(path):
    parsed = {}  # parte_no -> [sec, ...]
    cur_parte = None
    cur = None
    mode = None
    for raw in open(path, encoding="utf-8").read().splitlines():
        s = raw.rstrip("\n").rstrip()
        mp = re.match(r"^#{0,}\s*Part(?:ie|e)\s*(\d+)", s, re.I)
        if mp:
            cur_parte = int(mp.group(1))
            cur = None
            mode = None
            continue
        m_full = re.search(r"终极分类词\s+Section\s+(\d+)\s*(.*)$", s)
        if m_full:
            if cur_parte is None:
                continue
            cur = {"no": int(m_full.group(1)),
                   "name": m_full.group(2).strip(),
                   "w": [], "s": [], "e": []}
            parsed.setdefault(cur_parte, []).append(cur)
            mode = "table"
            continue
        if cur is None:
            continue
        if not s or s == "---":
            continue
        if "终极分类词" in s:
            mode = "table"
            continue
        if "经典" in s:
            mode = "s"
            continue
        if "拓展" in s or "扩展" in s:
            mode = "e"
            continue

        if mode == "table":
            # 制表符分隔的 4 列词表；首行中文表头跳过
            if "\t" in s:
                cells = [c.strip() for c in s.split("\t")]
                if len(cells) == 4 and cells[0] not in ("中文", "法语"):
                    e = mk_w(cells[0], cells[1], cells[2], cells[3])
                    if e:
                        cur["w"].append(e)
                continue
            # 非制表行（说明/空行）忽略
            continue
        elif mode == "s":
            if s.startswith("•") or s.startswith("-") or s.startswith("*"):
                r = im.parse_sentence(s)
                if r:
                    cur["s"].append(r)
            continue
        elif mode == "e":
            if re.match(r"^\s*\d+\b", s):
                r = parse_exp_local(s)
                if r:
                    cur["e"].append(r)
            continue
    return parsed


def parse_exp_local(line):
    """词汇大拓展: '1 volontario [ipa] pos. 中文'（数字后可为空格或标点）"""
    text = re.sub(r"^\s*\d+[.、)．]?\s*", "", line).strip()
    if not text:
        return None
    ipa = ""
    m = re.search(r"\[([^\]]*)\]", text)
    if m:
        ipa = m.group(1).strip()
        text = (text[:m.start()] + " " + text[m.end():]).strip()
    pos = ""
    m2 = im.POS_RE.search(text)
    if m2:
        pos = m2.group(1)
        text = (text[:m2.start()] + " " + text[m2.end():]).strip()
    it, zh = im.split_word_zh(text)
    if not it:
        return None
    if it.endswith(" pl."):
        it = it[:-4].strip()
    return [zh, it, pos, "", "", im.zh_py(zh), ipa]


def run(write=False):
    parsed = parse_raw(RAW)
    idx = im.load_audio_index()
    new_items = []
    for parte, gid in PARTE2GID.items():
        secs = parsed.get(parte, [])
        if not secs:
            print("  ! Parte %d 未解析到内容" % parte)
            continue
        data = im.load_sec_js(gid)
        by_no = {x["no"]: x for x in data["secs"]}
        total_w = total_s = total_e = 0
        for p in secs:
            tgt = by_no.get(p["no"])
            if tgt is None:
                print("  ! 跳过 Section %d（gid%d 无此节）" % (p["no"], gid))
                continue
            tgt["w"], tgt["s"], tgt["e"] = p["w"], p["s"], p["e"]
            for kind, fi, fz in (("w", 1, 0), ("e", 1, 0), ("s", 0, 1)):
                for row in tgt[kind]:
                    row[3] = im.audio_for(idx, "it", row[fi], new_items)
                    row[4] = im.audio_for(idx, "zh", row[fz], new_items)
            total_w += len(tgt["w"]); total_s += len(tgt["s"]); total_e += len(tgt["e"])
            print("  gid%-2d Section %-2d %-16s 词%-3d 句%-2d 拓%-2d"
                  % (gid, p["no"], p["name"], len(tgt["w"]), len(tgt["s"]), len(tgt["e"])))
        if write:
            im.write_sec_js(gid, data)
            im.sync_meta(gid, data)
        print("    -> gid%d 词%d 句%d 拓%d" % (gid, total_w, total_s, total_e))
    if write:
        im.save_audio_index(idx)
        with open(im.MANIFEST_PATH, "a", encoding="utf-8") as f:
            for it in new_items:
                f.write(__import__("json").dumps(it, ensure_ascii=False) + "\n")
        print("待生成音频 %d 个 → audio/_manifest.jsonl（累计编号 %d）"
              % (len(new_items), idx["counter"]))
    else:
        print("[DRY RUN] 加 --go 才真正写入 data/sec/16..20.js 与音频索引")


def dry_summary():
    parsed = parse_raw(RAW)
    for parte in sorted(parsed):
        print("Parte %d (gid%d):" % (parte, PARTE2GID[parte]))
        for p in parsed[parte]:
            print("  Sec%-2d %-16s 词%-3d 句%-2d 拓%-2d"
                  % (p["no"], p["name"], len(p["w"]), len(p["s"]), len(p["e"])))
    gw = sum(len(p["w"]) for v in parsed.values() for p in v)
    gs = sum(len(p["s"]) for v in parsed.values() for p in v)
    ge = sum(len(p["e"]) for v in parsed.values() for p in v)
    print("合计: 词%d 句%d 拓%d = %d 条" % (gw, gs, ge, gw + gs + ge))


if __name__ == "__main__":
    if "--go" in sys.argv:
        print("[WRITE]")
        run(write=True)
    elif "--summary" in sys.argv:
        dry_summary()
    else:
        print("[DRY RUN]")
        run(write=False)
