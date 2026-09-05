import json, asyncio, edge_tts, os

BASE = "D:/意大利语材料/15000意语单词随身背"
JS = os.path.join(BASE, "data/sec/0.js")
IDX = os.path.join(BASE, "audio/_index.json")

# ---- 1. fix data row ----
s = open(JS, encoding="utf-8").read()
pfx = "window.BOOK_DATA[0]="
start = s.index(pfx) + len(pfx)
end = s.rindex("}") + 1
obj = json.loads(s[start:end])

old_it = "Il primo maggio è la Festa dei Lavoratori, è un giorno di festa per tutti i francesi. 5"
new_it = "Il primo maggio è la Festa dei Lavoratori, è un giorno di festa per tutti gli italiani."
old_zh = "月1日是劳动节，这是所有法国人的节日"
new_zh = "5月1日是劳动节，这是所有意大利人的节日。"
new_py = "wǔ yuè yī rì shì láo dòng jié，zhè shì suǒ yǒu yì dà lì rén de jié rì"

hit = False
for sec in obj["secs"]:
    for r in sec.get("s", []):
        if r[0] == old_it and r[1] == old_zh:
            r[0] = new_it
            r[1] = new_zh
            r[5] = new_py
            hit = True
            print("MODIFIED  sec", sec["no"], sec["name"])
            print("  it:", r[0])
            print("  zh:", r[1])
            print("  py:", r[5])
            break
assert hit, "row not found!"

out = "window.BOOK_DATA=window.BOOK_DATA||{};window.BOOK_DATA[0]=" + \
      json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(JS, "w", encoding="utf-8").write(out)
print("0.js written")

# ---- 2. update audio cache ----
cache = json.load(open(IDX, encoding="utf-8"))
m = cache["map"]
old_k_it = "it|" + old_it
old_k_zh = "zh|" + old_zh
if old_k_it in m:
    del m[old_k_it]
if old_k_zh in m:
    del m[old_k_zh]
m["it|" + new_it] = "it/00585.mp3"
m["zh|" + new_zh] = "zh/00586.mp3"
json.dump(cache, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("cache updated")

# ---- 3. regenerate the two mp3s ----
async def synth(text, voice, path):
    comm = edge_tts.Communicate(text=text, voice=voice)
    await comm.save(path)
    print("audio ->", path, os.path.getsize(path), "bytes")

async def main():
    await synth(new_it, "it-IT-ElsaNeural", os.path.join(BASE, "audio/it/00585.mp3"))
    await synth(new_zh, "zh-CN-XiaoxiaoNeural", os.path.join(BASE, "audio/zh/00586.mp3"))

asyncio.run(main())
print("DONE")
