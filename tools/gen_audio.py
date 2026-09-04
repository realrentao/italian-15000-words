# -*- coding: utf-8 -*-
"""
根据 audio/_manifest.jsonl 用 edge_tts 库（进程内，并发）生成 mp3，支持断点续传。
意大利语 -> it-IT-ElsaNeural ；中文 -> zh-CN-XiaoxiaoNeural
"""
import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "audio", "_manifest.jsonl")
AUDIO = os.path.join(ROOT, "audio")
VOICES = {"it": "it-IT-ElsaNeural", "zh": "zh-CN-XiaoxiaoNeural"}
RATE = "-10%"
CONCURRENCY = 24


async def save_one(text, voice, fp):
    import edge_tts
    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(text, voice, rate=RATE)
            with open(fp, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
            if os.path.getsize(fp) >= 200:
                return True
        except Exception as e:
            if attempt == 2:
                sys.stderr.write("x %s :: %s\n" % (fp, e))
    return False


async def main():
    if not os.path.exists(MANIFEST):
        print("no manifest"); return
    rows = [json.loads(l) for l in open(MANIFEST, encoding="utf-8") if l.strip()]
    todo = []
    for r in rows:
        fp = os.path.join(AUDIO, r["file"])
        if not os.path.exists(fp) or os.path.getsize(fp) < 200:
            todo.append(r)
    print("manifest=%d  todo=%d" % (len(rows), len(todo)))
    if not todo:
        print("all done"); return

    sem = asyncio.Semaphore(CONCURRENCY)
    done = 0

    async def worker(r):
        nonlocal done
        fp = os.path.join(AUDIO, r["file"])
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        voice = VOICES.get(r["lang"])
        async with sem:
            ok = await save_one(r["text"], voice, fp)
        done += 1
        if done % 50 == 0:
            print("... %d/%d" % (done, len(todo)), flush=True)

    await asyncio.gather(*(worker(r) for r in todo))
    print("完成 %d/%d" % (done, len(todo)))


if __name__ == "__main__":
    asyncio.run(main())
