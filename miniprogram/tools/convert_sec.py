# -*- coding: utf-8 -*-
"""
把现有站点数据源（window.BOOK_META / window.BOOK_DATA[N] 的 JS 赋值文件）
转换为纯 JSON，供微信小程序 wx.request 按需拉取。

输入：
  <repo>/data/meta.js
  <repo>/data/sec/<N>.js
输出：
  <repo>/cdn-staging/meta.json
  <repo>/cdn-staging/sec/<N>.json

部署：把 cdn-staging/ 整个目录推到 GitHub Pages 仓库根目录（或任意 HTTPS CDN），
使 https://<your-cdn>/cdn-staging/meta.json 与 /cdn-staging/sec/<N>.json 可访问。
app.js 的 globalData.cdn 已指向仓库根，故此处输出到仓库根 cdn-staging/。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "cdn-staging")


def strip_js_assignment(text, prefix_re):
    """去掉 `prefix =` 与结尾分号，得到纯 JSON 文本。"""
    text = text.strip()
    m = re.match(prefix_re, text, re.S)
    if m:
        text = text[m.end():]
    # 去掉结尾的分号（可能多个）
    text = re.sub(r";+\s*$", "", text)
    return text


def convert_sec(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # window.BOOK_DATA=window.BOOK_DATA||{};window.BOOK_DATA[<N>]={...}
    prefix = r"^window\.BOOK_DATA=window\.BOOK_DATA\|\|\{\};window\.BOOK_DATA\[\d+\]="
    js = strip_js_assignment(raw, prefix)
    return json.loads(js)


def convert_meta(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    prefix = r"^window\.BOOK_META="
    js = strip_js_assignment(raw, prefix)
    return json.loads(js)


def main():
    os.makedirs(os.path.join(OUT, "sec"), exist_ok=True)

    # meta
    meta = convert_meta(os.path.join(DATA, "meta.js"))
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))
    grupos = meta.get("grupos", [])
    n_partes = sum(len(g.get("partes", [])) for g in grupos)
    n_secs = sum(len(p.get("secs", [])) for g in grupos for p in g.get("partes", []))
    print("meta.json ok | 大篇=%d 大类=%d 小节=%d" % (len(grupos), n_partes, n_secs))

    # sec
    sec_files = sorted(
        [f for f in os.listdir(os.path.join(DATA, "sec")) if f.endswith(".js")],
        key=lambda x: int(re.match(r"(\d+)\.js", x).group(1)),
    )
    total_w = total_s = total_e = 0
    for fn in sec_files:
        gid = int(re.match(r"(\d+)\.js", fn).group(1))
        d = convert_sec(os.path.join(DATA, "sec", fn))
        for sec in d.get("secs", []):
            total_w += len(sec.get("w", []))
            total_s += len(sec.get("s", []))
            total_e += len(sec.get("e", []))
        with open(os.path.join(OUT, "sec", "%d.json" % gid), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print("sec json ok | files=%d 词条 w=%d s=%d e=%d" % (len(sec_files), total_w, total_s, total_e))
    print("输出目录:", OUT)


if __name__ == "__main__":
    main()
