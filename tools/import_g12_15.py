# -*- coding: utf-8 -*-
"""
导入 Chapitre 3 人物与行为 / Partie 2–5 (gid=12..15)
源: tools/_g12_15_raw.md
格式:
  - 大部分 Section = 竖排4行组 (中文含词性前缀 / 意大利语 / [音标] / 词性) 各占一行
  - Partie 5 的 Sec2/3/4 = 连写单行: 中文法语音标词性名 情人amante[aˈmante]s.m.名 朋友...
复用 import_md 的 audio_for / write_sec_js / save_audio_index / sync_meta / zh_py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_md as im  # noqa

RAW = os.path.join(ROOT, "tools", "_g12_15_raw.md")
PARTE2GID = {2: 12, 3: 13, 4: 14, 5: 15}

CJK = re.compile(r"[\u4e00-\u9fff]")
POSPRE = re.compile(r"^(名|形|动|副|介|连|固|短|代|数|叹)\s+")
HEADER_TOKENS = {"中文", "法语", "音标", "词性", "意大利语"}
POS_SUFFIX = r"(s\.m\.|s\.f\.|v\.|agg\.|avv\.|prep\.|pron\.|cong\.|loc\.|num\.|interj\.|art\.|part\.)"


def zh_py(zh):
    return im.zh_py(zh)


def mk_w(zh, it, pos, ipa):
    """统一构造 w / e 行 7 字段 [zh, it, pos, it_mp3, zh_mp3, py, ipa]"""
    zh = POSPRE.sub("", zh).strip()
    if not zh or not it:
        return None
    return [zh, it.strip(), (pos or "").strip(), "", "", zh_py(zh), (ipa or "").strip()]


# ---------------- 竖排4行组 ----------------
def make_entry(buf):
    if len(buf) < 4:
        return None
    zh, it, ipa, pos = buf[0], buf[1], buf[2], buf[3]
    ipa = ipa.strip().lstrip("[").rstrip("]").strip()
    return mk_w(zh, it, pos, ipa)


# ---------------- 连写单行 ----------------
def parse_concat_seg(seg):
    m = re.match(r"^(名|形|动|副|数)\s+([\u4e00-\u9fff][\u4e00-\u9fff，、（）·\-。！？；：]*)\s*(.*)$", seg)
    if not m:
        return None
    zh = m.group(2).strip()
    rest = m.group(3)
    ipa = ""
    mm = re.search(r"\[([^\]]*)\]", rest)
    if mm:
        ipa = mm.group(1).strip()
        rest = (rest[:mm.start()] + " " + rest[mm.end():]).strip()
    pos = ""
    pm = re.search(POS_SUFFIX + r"\s*$", rest)
    if pm:
        pos = pm.group(1).strip()
        rest = rest[:pm.start()].strip()
    it = rest.strip()
    return mk_w(zh, it, pos, ipa)


def is_concat_line(line):
    s = line.strip()
    if s.startswith("中文法语音标词性"):
        return True
    # 单行内出现 >=2 个 词性前缀+汉字
    return len(re.findall(r"(?:名|形|动|副|数)\s*[\u4e00-\u9fff]", s)) >= 2


def parse_concat_line(line):
    s = re.sub(r"^中文法语音标词性", "", line.strip())
    out = []
    for seg in re.split(r"(?=(?:名|形|动|副|数)\s*[\u4e00-\u9fff])", s):
        seg = seg.strip()
        if not seg:
            continue
        r = parse_concat_seg(seg)
        if r:
            out.append(r)
    return out


# ---------------- 主解析 ----------------
def parse_raw(path):
    parsed = {}  # parte_no -> [sec, ...]
    cur_parte = None
    cur = None
    mode = None
    buf = []

    def flush_buf():
        nonlocal buf
        if buf:
            e = make_entry(buf)
            if e and cur is not None:
                cur["w"].append(e)
            buf = []

    for raw in open(path, encoding="utf-8").read().splitlines():
        line = raw.rstrip("\n")
        s = line.strip()
        mp = re.match(r"^#{0,}\s*Part(?:ie|e)\s*(\d+)", s, re.I)
        if mp:
            flush_buf()
            cur_parte = int(mp.group(1))
            cur = None
            mode = None
            continue
        # 「终极分类词 Section N NAME」精确匹配（本源每个 Section 都以此开头）
        m_full = re.search(r"终极分类词\s+Section\s+(\d+)\s+(.+)$", s)
        if m_full:
            flush_buf()
            cur = {"no": int(m_full.group(1)), "name": m_full.group(2).strip(),
                   "w": [], "s": [], "e": []}
            parsed.setdefault(cur_parte, []).append(cur)
            mode = "table"
            continue
        if cur is None:
            continue
        if not s or s == "---":
            continue
        if "终极分类词" in s:
            flush_buf()
            mode = "table"
            continue
        if "经典" in s:
            flush_buf()
            mode = "s"
            continue
        if "拓展" in s or "扩展" in s:
            flush_buf()
            mode = "e"
            continue
        if mode == "table":
            if s in HEADER_TOKENS:
                flush_buf()
                continue
            if is_concat_line(s):
                flush_buf()
                for r in parse_concat_line(s):
                    cur["w"].append(r)
            else:
                buf.append(s)
                if len(buf) == 4:
                    e = make_entry(buf)
                    if e:
                        cur["w"].append(e)
                    buf = []
        elif mode == "s":
            r = im.parse_sentence(line)
            if r:
                cur["s"].append(r)
        elif mode == "e":
            r = im.parse_expansion(line)
            if r:
                cur["e"].append(r)
    flush_buf()
    return parsed


# ---------------- 写入 ----------------
def run():
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
            print("  gid%-2d Section %-2d %-16s 词%-3d 句%-2d 拓%-2d"
                  % (gid, p["no"], p["name"], len(tgt["w"]), len(tgt["s"]), len(tgt["e"])))
        im.write_sec_js(gid, data)
        total_all = im.sync_meta(gid, data)
        print("    -> gid%d 写入完成，全书累计 %d 条" % (gid, total_all))
    im.save_audio_index(idx)
    with open(im.MANIFEST_PATH, "a", encoding="utf-8") as f:
        for it in new_items:
            f.write(__import__("json").dumps(it, ensure_ascii=False) + "\n")
    print("待生成音频 %d 个 → audio/_manifest.jsonl" % len(new_items))


if __name__ == "__main__":
    print("=== Parte 2 (gid12) ===")
    for p in parse_raw(RAW).get(2, []):
        print("  Sec%-2d %-16s 词%-3d 句%-2d 拓%-2d" % (p["no"], p["name"], len(p["w"]), len(p["s"]), len(p["e"])))
    print("=== Parte 3 (gid13) ===")
    for p in parse_raw(RAW).get(3, []):
        print("  Sec%-2d %-16s 词%-3d 句%-2d 拓%-2d" % (p["no"], p["name"], len(p["w"]), len(p["s"]), len(p["e"])))
    print("=== Parte 4 (gid14) ===")
    for p in parse_raw(RAW).get(4, []):
        print("  Sec%-2d %-16s 词%-3d 句%-2d 拓%-2d" % (p["no"], p["name"], len(p["w"]), len(p["s"]), len(p["e"])))
    print("=== Parte 5 (gid15) ===")
    for p in parse_raw(RAW).get(5, []):
        print("  Sec%-2d %-16s 词%-3d 句%-2d 拓%-2d" % (p["no"], p["name"], len(p["w"]), len(p["s"]), len(p["e"])))
    if "--go" in sys.argv:
        print("\n[WRITE]")
        run()
    else:
        print("\n[DRY RUN] 加 --go 才真正写入 data/sec/12..15.js")
