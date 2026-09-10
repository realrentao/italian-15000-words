#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-record Italian audio for the numbered-word fixes.
Reads tools/_reco_numbered.json: list of [audio_rel, text].
Overwrites audio/<rel> with edge-tts (it-IT-ElsaNeural, -10%)."""
import json, os, asyncio, edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
reco = json.load(open(os.path.join(ROOT, 'tools/_reco_numbered.json'), encoding='utf-8'))
VOICE = 'it-IT-ElsaNeural'
RATE = '-10%'

async def gen(rel, text):
    out = os.path.join(ROOT, 'audio', rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=RATE)
            await comm.save(out)
            return True
        except Exception as e:
            if attempt == 2:
                print(f'FAIL {rel} "{text}": {e}')
                return False
    return False

async def main():
    ok = 0
    for rel, text in reco:
        if await gen(rel, text):
            ok += 1
    print(f'Re-recorded {ok}/{len(reco)} Italian audio files.')

asyncio.run(main())
