# -*- coding: utf-8 -*-
"""
导入 Chapitre 社会（政治与经济） / 11 个 Partie -> gid 34..42 + 47,48
源: tools/_social_raw.md
格式（管道表格，与 Chapitre6 一致）:
  - 终极分类词 w 表: | 词性 | 中文 | 意大利语 | 音标 | 性数 |
  - 经典法语句 s   : • 例 `意大利语` 中文翻译。——《出处》
  - 词汇大拓展 e 表: | # | 意大利语 | 音标 | 词性 | 中文 |
文档 Partie 顺序 -> gid 映射（沿用原骨架 gid34-42，文化与艺术/房地产 用新 gid 47/48）:
  1 政治相关->34  2 经济基本知识->35  3 经济行为->36  4 宗教->37
  5 文化与艺术->47(新)  6 传媒->38  7 法律与犯罪->39  8 法院->40
  9 军事->41  10 航空航天->42  11 房地产->48(新)
"以文档分类为准" = 用 md 段落结构【重建】社会大篇 11 个 parte（含 2 个新增 gid），
并同步 meta.js（GRUPO 社会 的 partes 顺序/名称/节数按文档重排）。
复用 import_md 的 audio_for / write_sec_js / load_sec_js / zh_py / split_word_zh /
            load_audio_index / save_audio_index / POS_RE
"""
import os
import re
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_md as im  # noqa

RAW = os.path.join(ROOT, "tools", "_social_raw.md")
GNAME = "社会"
# 文档 Partie 顺序 -> gid（忽略 md 里如果编号错乱，这里 md 是 1..11 顺序）
PARTE_IDX2GID = {1: 34, 2: 35, 3: 36, 4: 37, 5: 47, 6: 38,
                 7: 39, 8: 40, 9: 41, 10: 42, 11: 48}

# 扩展词性识别（补全 n./m./f./avv./v.pr. 等 import_md 默认缺的）
im.POS_RE = re.compile(
    r"\b(n\.m\.|n\.f\.|n\.|m\.|f\.|v\.t\.|v\.i\.|v\.r\.|v\.pr\.|adj\.|adv\.|avv\.|prep\.|"
    r"pron\.|cong\.|inter\.|num\.|art\.|agg\.|s\.m\.|s\.f\.|m\.inv|f\.inv|inv\.|pl\.|"
    r"pref\.|r\.|i\.|pr\.|a\.|loc\.)", re.I)

CJK = re.compile(u"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")


def strip_star(s):
    return s.replace("*", "").replace("`", "").strip()


def parse_sentence_local(line):
    """经典句：剥掉 •/-/* 子弹与「例」字、去反引号，再交给标准 parse_sentence。"""
    t = re.sub(r"^\s*[•\-*]\s*", "", line)
    t = re.sub(r"^例\s*", "", t.strip())
    t = t.replace("`", "")
    if not t:
        return None
    return im.parse_sentence(t)


def parse_exp_local(line):
    """词汇大拓展: '1 decompressione [ipa] s.f. 减压'（数字后可为空格/标点）"""
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
    if not it or not zh:
        return None
    return [zh, it, pos, "", "", im.zh_py(zh), ipa]


def parse_raw(path):
    parsed = {}          # parte_idx -> {'name':..., 'secs':[...]}
    cur_parte_idx = None
    cur = None
    mode = None
    parte_counter = 0
    for raw in open(path, encoding="utf-8").read().splitlines():
        s = raw.rstrip()
        # ---- Partie 头（按出现顺序编号）----
        mp = re.match(r"^\s*#{1,6}\s*Part(?:ie|e)\s*(\d+)\s*(.*)$", s, re.I)
        if mp:
            parte_counter += 1
            cur_parte_idx = parte_counter
            parsed[cur_parte_idx] = {
                "name": mp.group(2).strip(),
                "secs": [],
            }
            cur = None
            mode = None
            continue
        # ---- Section 头 ----
        ms = re.match(r"^\s*#{1,6}\s*Section\s+(\d+)\s*(.*)$", s, re.I)
        if ms:
            if cur_parte_idx is None:
                continue
            name = ms.group(2).strip()
            name = re.sub(r"\s+p\.\d+.*$", "", name).strip()  # 去掉页码后缀
            cur = {"no": int(ms.group(1)), "name": name,
                   "w": [], "s": [], "e": []}
            parsed[cur_parte_idx]["secs"].append(cur)
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
        if "其他" in s:
            mode = "other"
            continue

        if (mode in ("table", "e")) and s.startswith("|"):
            cells = [strip_star(c) for c in s.strip("|").split("|")]
            if len(cells) < 4:
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            # w 表头
            if cells[0] == "词性":
                continue
            # e 表（首列 # 或数字）
            if cells[0] == "#" or re.match(r"^\d+$", cells[0]):
                if cells[0] == "#" and cells[1] == "意大利语":
                    continue  # e 表头
                # e 行: #|意大利语|音标|词性|中文
                if len(cells) < 5:
                    continue
                it, ipa, pos, zh = cells[1], cells[2], cells[3], cells[4]
                ipa2 = ipa.strip().lstrip("[").rstrip("]").strip()
                if it and zh:
                    cur["e"].append([zh, it, pos, "", "", im.zh_py(zh), ipa2])
                continue
            # w 行: 词性|中文|意大利语|音标|性数
            if len(cells) < 5:
                continue
            pos, zh, it, ipa, gender = cells[0], cells[1], cells[2], cells[3], cells[4]
            if not (zh and it):
                continue
            pos_label = pos if gender in ("", "-") else "%s %s" % (pos, gender)
            ipa2 = ipa.strip().lstrip("[").rstrip("]").strip()
            cur["w"].append([zh, it, pos_label, "", "", im.zh_py(zh), ipa2])
            continue
        elif mode == "s":
            if re.match(r"^\s*[•\-*]\s+", s):
                r = parse_sentence_local(s)
                if r:
                    cur["s"].append(r)
            continue
        elif mode == "e":
            if re.match(r"^\s*\d+[.、)．]?\s", s):
                r = parse_exp_local(s)
                if r:
                    cur["e"].append(r)
            continue
        elif mode == "other":
            if re.match(r"^\s*[•\-*]\s+", s):
                t = re.sub(r"^\s*[•\-*]\s*", "", s).strip()
                if "插图标注" in t:
                    rest = re.split(r"[：:]", t, maxsplit=1)[-1].strip()
                    it, zh = im.split_word_zh(rest)
                    if it and zh:
                        cur["w"].append([zh, it, "", "", "", im.zh_py(zh), ""])
            continue
    return parsed


def dedupe_rows(parsed):
    """同节内按 (zh,it,pos,ipa) 去重，保留首次出现。"""
    for parte in parsed.values():
        for sec in parte["secs"]:
            for kind in ("w", "s", "e"):
                seen = set()
                kept = []
                for row in sec[kind]:
                    if kind in ("w", "e"):
                        key = (row[0], row[1], row[2], row[6])
                    else:
                        key = (row[0], row[1])
                    if key in seen:
                        continue
                    seen.add(key)
                    kept.append(row)
                sec[kind] = kept


def sync_meta_social():
    """重建 meta.js 中 社会 大篇（GRUPO 名=社会）的 11 个 parte，按文档顺序。"""
    p = os.path.join(ROOT, "data", "meta.js")
    s = open(p, encoding="utf-8").read()
    meta = json.JSONDecoder().raw_decode(s[s.index("=") + 1:])[0]
    gi = None
    for i, g in enumerate(meta["grupos"]):
        if g["name"] == GNAME:
            gi = i
            break
    assert gi is not None, "未找到 %r 大篇" % GNAME
    new_partes = []
    for parte_idx in sorted(PARTE_IDX2GID):
        gid = PARTE_IDX2GID[parte_idx]
        data = im.load_sec_js(gid)
        new_partes.append({
            "gid": gid,
            "no": parte_idx,
            "name": data.get("name", ""),
            "secs": [
                {"no": sc["no"], "name": sc["name"],
                 "w": len(sc["w"]), "s": len(sc["s"]), "e": len(sc["e"])}
                for sc in data["secs"]
            ],
        })
    meta["grupos"][gi]["partes"] = new_partes
    meta["totalAll"] = sum(
        sc["w"] + sc["s"] + sc["e"]
        for g in meta["grupos"] for pt in g["partes"] for sc in pt["secs"])
    body = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    with open(p, "w", encoding="utf-8") as f:
        f.write("window.BOOK_META=%s;\n" % body)
    return meta["totalAll"]


def run(write=False):
    parsed = parse_raw(RAW)
    dedupe_rows(parsed)
    idx = im.load_audio_index()
    new_items = []
    for parte_idx in sorted(parsed):
        gid = PARTE_IDX2GID.get(parte_idx)
        if gid is None:
            print("  ! Parte 序号 %d 无对应 gid，跳过" % parte_idx)
            continue
        p = parsed[parte_idx]
        secs = p["secs"]
        if not secs:
            print("  ! Parte %d (gid%d) 无 Section" % (parte_idx, gid))
            continue
        try:
            old = im.load_sec_js(gid)
        except (FileNotFoundError, IOError, ValueError):
            old = {}
        # 重建：保留 gid / gname，name 取 md（空则保留旧名），no=parte_idx
        name = p["name"] or old.get("name", "")
        data = {
            "gid": gid,
            "no": parte_idx,
            "name": name,
            "gname": old.get("gname", GNAME),
            "secs": [{"no": sc["no"], "name": sc["name"],
                      "w": sc["w"], "s": sc["s"], "e": sc["e"]}
                     for sc in secs],
        }
        total_w = total_s = total_e = 0
        for sc in data["secs"]:
            for kind, fi, fz in (("w", 1, 0), ("e", 1, 0), ("s", 0, 1)):
                for row in sc[kind]:
                    row[3] = im.audio_for(idx, "it", row[fi], new_items)
                    row[4] = im.audio_for(idx, "zh", row[fz], new_items)
            total_w += len(sc["w"]); total_s += len(sc["s"]); total_e += len(sc["e"])
        if write:
            im.write_sec_js(gid, data)
            print("  gid%-2d %-10s 节数%-3d 词%-4d 句%-3d 拓%-3d"
                  % (gid, name, len(secs), total_w, total_s, total_e))
        else:
            print("  [dry] gid%-2d %-10s 节数%-3d 词%-4d 句%-3d 拓%-3d"
                  % (gid, name, len(secs), total_w, total_s, total_e))
    if write:
        sync_meta_social()
        im.save_audio_index(idx)
        with open(im.MANIFEST_PATH, "a", encoding="utf-8") as f:
            for it in new_items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        print("待生成音频 %d 个 → audio/_manifest.jsonl（累计编号 %d）"
              % (len(new_items), idx["counter"]))
    else:
        print("[DRY RUN] 加 --go 才真正写入 data/sec + meta.js + 音频索引")


def dry_summary():
    parsed = parse_raw(RAW)
    dedupe_rows(parsed)
    gw = gs = ge = 0
    for parte_idx in sorted(parsed):
        p = parsed[parte_idx]
        gid = PARTE_IDX2GID.get(parte_idx)
        print("Parte %d (gid%d) %s:" % (parte_idx, gid, p["name"]))
        for sc in p["secs"]:
            print("  Sec%-3d %-18s 词%-3d 句%-2d 拓%-2d"
                  % (sc["no"], sc["name"], len(sc["w"]), len(sc["s"]), len(sc["e"])))
            gw += len(sc["w"]); gs += len(sc["s"]); ge += len(sc["e"])
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
