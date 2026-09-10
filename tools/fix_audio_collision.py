#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix Intesa Sanpaolo / capelli audio collision.
- it/06276.mp3 + zh/06277.mp3 -> regenerate as the BANK's audio (Intesa Sanpaolo / 联合圣保罗银行) so 7.js is correct.
- capelli (8.js) gets fresh files it/07828.mp3 + zh/07829.mp3 (capelli / 头发).
"""
import os, asyncio, edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IT_VOICE, ZH_VOICE, RATE = 'it-IT-ElsaNeural', 'zh-CN-XiaoxiaoNeural', '-10%'

async def gen(rel, text, voice):
    out = os.path.join(ROOT, 'audio', rel)
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate=RATE).save(out)
            return True
        except Exception as e:
            if attempt == 2:
                print('FAIL', rel, text, e); return False
    return False

async def main():
    # bank (7.js Intesa Sanpaolo)
    await gen('it/06276.mp3', 'Intesa Sanpaolo', IT_VOICE)
    await gen('zh/06277.mp3', '联合圣保罗银行', ZH_VOICE)
    # capelli (8.js)
    await gen('it/07828.mp3', 'capelli', IT_VOICE)
    await gen('zh/07829.mp3', '头发', ZH_VOICE)
    print('regenerated 4 files')

asyncio.run(main())
