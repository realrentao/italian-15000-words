# -*- coding: utf-8 -*-
"""
导入 Chapitre 5 求职 / Partie 1–4 -> gid 21..24
源: tools/_ch5_raw.md
格式 (与 Chapitre 4 不同，本次是管道表格 + 加粗表头 + 「法语」列名 + 「-」例句):
  - 词表为管道分隔 4 列: | **中文(含词性前缀)** | **法语(=意大利语)** | **音标** | **词性** |
  - 经典句: - 意大利语. 中文翻译。——《出处》
  - 拓展:   1 意语 [ipa] pos. 中文
复用 import_md 的 audio_for / write_sec_js / save_audio_index / sync_meta / zh_py /
            load_sec_js / parse_sentence / split_word_zh
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_md as im  # noqa

RAW = os.path.join(ROOT, "tools", "_ch5_raw.md")
PARTE2GID = {1: 21, 2: 22, 3: 23, 4: 24}

# 中文列里可能带的词性前缀（需剥离，避免「名 广告」重复显示）
POSPRE = re.compile(r"^(名|形|动|副|介|连|固|短|代|数|叹|量)\s+")

# 扩展词性识别（补全 n./m./f./avv./v.pr./pref. 等 import_md 默认缺的）
im.POS_RE = re.compile(
    r"\b(n\.m\.|n\.f\.|n\.|m\.|f\.|v\.t\.|v\.i\.|v\.r\.|v\.pr\.|adj\.|adv\.|avv\.|prep\.|"
    r"pron\.|cong\.|inter\.|num\.|art\.|agg\.|s\.m\.|s\.f\.|m\.inv|f\.inv|inv\.|pl\.|"
    r"pref\.|r\.|i\.|pr\.|a\.|loc\.)", re.I)


def strip_star(s):
    return s.replace("*", "").strip()


def mk_w(zh_raw, it, ipa, pos):
    """构造 w / e 行 7 字段 [zh, it, pos, it_mp3, zh_mp3, py, ipa]"""
    zh = POSPRE.sub("", zh_raw).strip()
    it = (it or "").strip()
    if not zh or not it:
        return None
    ipa = (ipa or "").strip().lstrip("[").rstrip("]").strip()
    pos = (pos or "").strip()
    return [zh, it, pos, "", "", im.zh_py(zh), ipa]


def parse_exp_local(line):
    """词汇大拓展: '1 necessità [ipa] pos. 中文'（数字后可为空格/标点）"""
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


def parse_raw(path):
    parsed = {}  # parte_no -> [sec, ...]
    cur_parte = None
    cur = None
    mode = None
    for raw in open(path, encoding="utf-8").read().splitlines():
        s = raw.rstrip()
        mp = re.match(r"^\s*#{1,6}\s*Part(?:ie|e)\s*(\d+)", s, re.I)
        if mp:
            cur_parte = int(mp.group(1))
            cur = None
            mode = None
            continue
        # Section 起点：### Section N 名称 或 终极分类词 Section N 名称
        m_full = re.match(r"^\s*#{1,6}\s*Section\s+(\d+)\s*(.*)$", s, re.I)
        m_full2 = re.search(r"终极分类词\s+Section\s+(\d+)\s*(.*)$", s)
        if m_full or m_full2:
            if cur_parte is None:
                continue
            mm = m_full or m_full2
            cur = {"no": int(mm.group(1)),
                   "name": (mm.group(2) if mm.lastindex >= 2 else "").strip(),
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
            if s.startswith("|"):
                cells = [strip_star(c) for c in s.strip("|").split("|")]
                if len(cells) < 4:
                    continue
                # 分隔行（全为 - : 空格）
                if set("".join(cells)) <= set("-: "):
                    continue
                # 表头行：中文/意大利语/法语
                if (cells[0] in ("中文", "") and cells[1] in ("意大利语", "法语", "")) or \
                   cells[0] == "中文":
                    continue
                e = mk_w(cells[0], cells[1], cells[2], cells[3])
                if e:
                    cur["w"].append(e)
            continue
        elif mode == "s":
            if re.match(r"^\s*[-*]\s+", s):
                r = im.parse_sentence(s)
                if r:
                    cur["s"].append(r)
            continue
        elif mode == "e":
            if re.match(r"^\s*\d+[.、)．]?\s", s):
                r = parse_exp_local(s)
                if r:
                    cur["e"].append(r)
            continue
    return parsed


def dedupe_rows(parsed):
    """同节内按 (zh,it,pos,ipa) 去重，保留首次出现。"""
    for parte, secs in parsed.items():
        for sec in secs:
            for kind in ("w", "s", "e"):
                seen = set()
                kept = []
                for row in sec[kind]:
                    if kind == "w" or kind == "e":
                        key = (row[0], row[1], row[2], row[6])
                    else:  # s
                        key = (row[0], row[1])
                    if key in seen:
                        continue
                    seen.add(key)
                    kept.append(row)
                sec[kind] = kept


def run(write=False):
    parsed = parse_raw(RAW)
    dedupe_rows(parsed)
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
            print("  gid%-2d Section %-2d %-14s 词%-3d 句%-2d 拓%-2d"
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
        print("[DRY RUN] 加 --go 才真正写入 data/sec/21..24.js 与音频索引")


def dry_summary():
    parsed = parse_raw(RAW)
    dedupe_rows(parsed)
    for parte in sorted(parsed):
        print("Parte %d (gid%d):" % (parte, PARTE2GID[parte]))
        for p in parsed[parte]:
            print("  Sec%-2d %-14s 词%-3d 句%-2d 拓%-2d"
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
