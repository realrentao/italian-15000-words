# -*- coding: utf-8 -*-
"""把「生活设施 · Parte 5 常见商店」粘贴文本 tools/_g9p5_raw.md 导入 data/sec/9.js
布局兼容「4 行一组竖排」与「连写单行」。解析/音频/拼音/meta 同步统一走 pg_parse。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pg_parse

RAW = os.path.join(ROOT, "tools", "_g9p5_raw.md")
GID = 9

if __name__ == "__main__":
    pg_parse.run(GID, RAW)
