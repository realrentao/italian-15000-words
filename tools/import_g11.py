# -*- coding: utf-8 -*-
"""
导入 Chapitre 3 人物与行为 / Partie 1 人的特征 (gid=11)
源: tools/_g11_raw.md  (用户粘贴的 markdown，含 ** 粗体 + 中文列混了词性前缀)
预处理: 去 ** ; 剥掉中文列首的 名/形/动/副 等词性前缀
解析: 复用 pg_parse.parse_raw (管道表格 + 终极分类词/经典/拓展 三模式)
注意: pg_parse.parse_raw / run 接收的是【文件路径】，故清洗后落盘再传。
"""
import re
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pg_parse  # noqa

RAW_PATH = os.path.join(ROOT, "tools", "_g11_raw.md")
CLEAN_PATH = os.path.join(ROOT, "tools", "_g11_clean.md")
GID = 11

# 中文列首可能出现的词性前缀（与 pg_parse.CN2IT 对齐，含"量"备用）
POSPRE = re.compile(r"^(名|形|动|副|介|连|固|短|代|数|叹|量)\s+")


def preprocess(text):
    out = []
    for line in text.splitlines():
        line = line.replace("**", "")
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 2:
                cells[0] = POSPRE.sub("", cells[0])
            line = "| " + " | ".join(cells) + " |"
        out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    raw = open(RAW_PATH, encoding="utf-8").read()
    cleaned = preprocess(raw)
    open(CLEAN_PATH, "w", encoding="utf-8").write(cleaned)

    secs = pg_parse.parse_raw(CLEAN_PATH)
    total = 0
    for p in secs:
        print("Section %-2d %-18s w=%-3d s=%-2d e=%-2d"
              % (p["no"], p["name"], len(p["w"]), len(p["s"]), len(p["e"])))
        total += len(p["w"]) + len(p["s"]) + len(p["e"])
    print("TOTAL items:", total, "| sections parsed:", len(secs))
    if "--go" not in sys.argv:
        print("\n[DRY RUN] 加 --go 才真正写入 data/sec/11.js")
    else:
        pg_parse.run(GID, CLEAN_PATH)
