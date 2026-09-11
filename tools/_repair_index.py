import json, os, re, glob, sys, io

ROOT = r"D:\意大利语材料\15000意语单词随身背"
SEC = os.path.join(ROOT, "data", "sec")
IDX = os.path.join(ROOT, "audio", "_index.json")
MAN = os.path.join(ROOT, "audio", "_manifest.jsonl")

_log = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    _log.append(s)

def ref_paths():
    refs = set()
    for p in sorted(glob.glob(os.path.join(SEC, "*.js"))):
        s = open(p, encoding="utf-8").read()
        start = s.index("{", s.index("BOOK_DATA["))
        obj = json.JSONDecoder().raw_decode(s[start:])[0]
        for sc in obj["secs"]:
            for k in ("w", "s", "e"):
                for row in sc.get(k, []):
                    for cell in row:
                        if isinstance(cell, str):
                            mm = re.search(r"(it|zh)/(\d+)\.mp3$", cell)
                            if mm:
                                refs.add(mm.group(0))
    return refs

def num_of(path):
    m = re.search(r"(\d+)\.mp3$", path or "")
    return int(m.group(1)) if m else None

refs = ref_paths()
boundary = max(num_of(r) for r in refs)
log("max referenced path num : %d" % boundary)
log("total referenced paths  : %d" % len(refs))

idx = json.load(open(IDX, encoding="utf-8"))
mp = idx.get("map", {})
ghost_map = {k: v for k, v in mp.items() if (num_of(v) or -1) > boundary}
log("index counter (now)     : %d" % idx.get("counter"))
log("index map total         : %d" % len(mp))
log("GHOST map entries        : %d" % len(ghost_map))

man_lines = [l for l in open(MAN, encoding="utf-8").read().splitlines() if l.strip()]
ghost_man = []
keep_man = []
for ln in man_lines:
    mm = re.search(r"(it|zh)/(\d+)\.mp3", ln)
    if mm and int(mm.group(2)) > boundary:
        ghost_man.append(ln)
    else:
        keep_man.append(ln)
log("manifest total lines    : %d" % len(man_lines))
log("GHOST manifest lines    : %d" % len(ghost_man))

log("--- sample ghost map (first 10) ---")
for k, v in list(ghost_map.items())[:10]:
    log("   %s -> %s" % (k, v))

if "--fix" in sys.argv:
    new_map = {k: v for k, v in mp.items() if (num_of(v) or -1) <= boundary}
    idx["map"] = new_map
    idx["counter"] = boundary + 1
    json.dump(idx, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(MAN, "w", encoding="utf-8").write("\n".join(keep_man) + ("\n" if keep_man else ""))
    log("\n[FIX APPLIED] counter -> %d, map %d->%d, manifest %d->%d" % (
        idx["counter"], len(mp), len(new_map), len(man_lines), len(keep_man)))
else:
    log("\n(DRY) rerun with --fix to apply repair")

open(os.path.join(ROOT, "tools", "_repair_out.txt"), "w", encoding="utf-8").write("\n".join(_log) + "\n")
