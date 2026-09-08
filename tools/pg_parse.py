# -*- coding: utf-8 -*-
"""
解析「生活设施」系列粘贴文本（在邮局 / 在银行 等），兼容两种布局：
  1) 标准竖排：终极分类词 4 行一组 = 中文/意大利语/[音标]/词性
  2) 连写单行：中文法语音标词性货valuta[vaˈluːta]n.f.钱denaro[...]n.m.……
另外解析「经典法语句」（裸句，含可选 ——《出处》）与「词汇大拓展」（N. it [ipa] pos zh）。
复用 import_md 的音频去重 / 拼音 / meta 同步逻辑。
"""
import os
import re
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_md as im  # 需要 pypinyin

MANIFEST_PATH = os.path.join(ROOT, "audio", "_manifest.jsonl")
CJK = re.compile(u"[\u4e00-\u9fff]")

CN2IT = {"形": "adj.", "名": "n.", "副": "adv.", "动": "v.", "介": "prep.",
         "连": "cong.", "固": "loc.", "短": "loc.", "代": "pron.", "数": "num.",
         "叹": "inter."}
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
    if pos_idx < 0:
        if toks and len(toks[-1]) == 1 and toks[-1] in CN2IT:
            pos_idx, pos = len(toks) - 1, toks[-1]
    if pos_idx < 0:
        it, zh = split_word_zh(text)
        if not it or not zh:
            return None
        return [zh, it, "", "", "", im.zh_py(zh), ipa]
    before = " ".join(toks[:pos_idx]).strip()
    after = " ".join(toks[pos_idx + 1:]).strip()
    if after and CJK.search(after):
        it, zh = before, after
    elif CJK.search(before):
        zh, it = split_word_zh(before)
    else:
        it, zh = before, after
    it = it.strip()
    if not it:
        return None
    return [zh.strip(), it, norm_pos(pos), "", "", im.zh_py(zh.strip()), ipa]


# ---------- 连写单行（Section 3/4/5 在银行等） ----------

HEADER_TOKENS = {"中文", "法语", "音标", "词性", "意大利语"}


def _strip_header_prefix(s):
    s = re.sub(r"^中文法语音标词性", "", s)
    s = re.sub(r"^中文法语音标词性", "", s)
    return s


def parse_concat_entry(e):
    e = e.strip()
    if not e:
        return None
    m = re.match(r"^([\u4e00-\u9fff]+)(.*)$", e, re.S)
    if not m:
        return None
    zh = m.group(1)
    rest = m.group(2).strip()
    ipa = ""
    mm = re.search(r"\[([^\]]*)\]", rest)
    if mm:
        ipa = mm.group(1).strip()
        rest = (rest[:mm.start()] + " " + rest[mm.end():]).strip()
    pos = ""
    pm = re.search(r"([a-zA-Z]+(?:\.[a-zA-Z]+)*\.?)\s*$", rest)
    if pm:
        pos = pm.group(1).strip()
        rest = rest[:pm.start()].strip()
    it = rest.strip()
    if not it:
        return None
    return [zh, it, norm_pos(pos), "", "", im.zh_py(zh), ipa]


def parse_concat_lines(tbl):
    out = []
    parts = []
    for l in tbl:
        s = l.strip()
        if s in HEADER_TOKENS:
            continue
        s = _strip_header_prefix(s)
        if s:
            parts.append(s)
    text = "".join(parts)
    if not text:
        return out
    entries = re.split(r"(?<=\.)(?=[\u4e00-\u9fff])", text)
    for e in entries:
        r = parse_concat_entry(e)
        if r:
            out.append(r)
    return out


def is_concatenated(tbl):
    for l in tbl:
        if _strip_header_prefix(l.strip()).count("[") >= 2:
            return True
    return False


# ---------- markdown 管道表格（| 中文 | 意大利语 | 音标 | 词性 |） ----------


def _pipe_cells(s):
    cells = [c.strip() for c in s.strip().strip("|").split("|")]
    return [c for c in cells if c]


def _is_sep_row(cells):
    return bool(cells) and all(re.match(r"^[-:= ]+$", c) for c in cells)


def _is_header_row(cells):
    return bool(cells) and all(c in HEADER_TOKENS for c in cells)


def parse_table_rows(tbl):
    """markdown 表格行：| 中文 | 意/法语 | [音标] | 词性 |"""
    out = []
    for l in tbl:
        s = l.strip()
        if not s.startswith("|"):
            continue
        cells = _pipe_cells(s)
        if _is_header_row(cells) or _is_sep_row(cells) or len(cells) < 2:
            continue
        zh, it = cells[0], cells[1]
        if not CJK.search(zh) or not it:
            continue
        ipa, pos = "", ""
        for c in cells[2:]:
            m = re.search(r"\[([^\]]*)\]", c)
            if m:
                ipa = m.group(1).strip()
                c = (c[:m.start()] + c[m.end():]).strip()
            if c and is_pos(c):
                pos = c
        out.append([zh, it, norm_pos(pos), "", "", im.zh_py(zh), ipa])
    return out


def is_pipe_table(tbl):
    for l in tbl:
        s = l.strip()
        if not s.startswith("|"):
            continue
        cells = _pipe_cells(s)
        if not cells or _is_header_row(cells) or _is_sep_row(cells):
            continue
        return True
    return False


# ---------- 标准竖排（4 行一组） ----------

def _make_entry(buf):
    if not buf:
        return None
    zh = buf[0] if len(buf) > 0 else ""
    it = buf[1] if len(buf) > 1 else ""
    ipa = (buf[2] if len(buf) > 2 else "").strip().lstrip("[").rstrip("]").strip()
    pos = buf[3] if len(buf) > 3 else ""
    if not zh or not it:
        return None
    return [zh, it, norm_pos(pos), "", "", im.zh_py(zh), ipa]


def parse_vertical(tbl):
    out = []
    buf = []
    for l in tbl:
        s = l.strip()
        if s in HEADER_TOKENS:
            if buf:
                e = _make_entry(buf)
                if e:
                    out.append(e)
                buf = []
            continue
        buf.append(s)
        if len(buf) == 4:
            e = _make_entry(buf)
            if e:
                out.append(e)
            buf = []
    if buf:
        e = _make_entry(buf)
        if e:
            out.append(e)
    return out


def parse_raw(path):
    secs = []
    cur = None
    mode = None
    tbl = []

    def flush_tbl():
        nonlocal tbl
        if tbl and cur is not None:
            if is_pipe_table(tbl):
                rows = parse_table_rows(tbl)
            elif is_concatenated(tbl):
                rows = parse_concat_lines(tbl)
            else:
                rows = parse_vertical(tbl)
            cur["w"].extend(rows)
        tbl = []

    for raw in open(path, encoding="utf-8").read().splitlines():
        line = raw.rstrip("\n")
        s = line.strip()
        m = re.search(r"Section\s+(\d+)\s+(.+)$", s)
        if m:
            flush_tbl()
            cur = {"no": int(m.group(1)), "name": m.group(2).strip(),
                   "w": [], "s": [], "e": []}
            secs.append(cur)
            mode = "table"
            continue
        if re.match(r"^[#\s]*Part(?:ie|e)\b", s):
            flush_tbl()
            mode = None
            continue
        if cur is None:
            continue
        if not s or s == "---":
            continue
        if "终极分类词" in s:
            flush_tbl()
            mode = "table"
            continue
        if "经典" in s:
            flush_tbl()
            mode = "s"
            continue
        if "拓展" in s or "扩展" in s:
            flush_tbl()
            mode = "e"
            continue
        if mode == "table":
            tbl.append(s)
        elif mode == "s":
            r = parse_sentence(line)
            if r:
                cur["s"].append(r)
        elif mode == "e":
            r = parse_expansion(line)
            if r:
                cur["e"].append(r)
    flush_tbl()
    return secs


def run(GID, RAW):
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
    data["secs"] = parsed
    im.write_sec_js(GID, data)
    im.save_audio_index(idx)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        for it in new_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    total_all = im.sync_meta(GID, data)
    print("已写入 data/sec/%d.js；meta 同步（全书累计 %d 条）" % (GID, total_all))
    print("待生成音频 %d 个 → audio/_manifest.jsonl" % len(new_items))
    return parsed


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) >= 3:
        run(int(_sys.argv[1]), _sys.argv[2])
