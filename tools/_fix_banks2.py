# -*- coding: utf-8 -*-
"""把 gid7 Sec1 里剩余两家法国银行替换为意大利本土银行。"""
import re

P = "data/sec/7.js"
s = open(P, encoding="utf-8").read()

repl = [
    # 兴业银行 / Société Générale (法国) -> 锡耶纳牧山银行 / Banca Monte dei Paschi di Siena
    (r'\["兴业银行","Société Générale"[^\]]*\]',
     '["锡耶纳牧山银行","Banca Monte dei Paschi di Siena","n.f.","it/06280.mp3","zh/06281.mp3","xī yē nà mù shān yín háng","ˈbaŋka ˈmonte dei ˈpaski di ˈsjɛːna"]'),
    # 农业信贷银行 / Crédit Agricole (法国) -> 梅迪奥拉努姆银行 / Banca Mediolanum
    (r'\["农业信贷银行","Crédit Agricole"[^\]]*\]',
     '["梅迪奥拉努姆银行","Banca Mediolanum","n.f.","it/06282.mp3","zh/06283.mp3","méi dí ào lā nǔ mǔ yín háng","ˈbaŋka medjoˈlaːnum"]'),
]

cnt = 0
for pat, new in repl:
    if re.search(pat, s):
        s = re.sub(pat, new, s, count=1)
        cnt += 1
    else:
        print("WARN pattern not found:", pat[:40])

open(P, "w", encoding="utf-8").write(s)
print("replaced", cnt)
