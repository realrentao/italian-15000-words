// 审计全站词性标签分布 + 提取所有动词原形（用于逐词判助动词 avere/essere）
const fs = require("fs");
const vm = require("vm");
const dir = "data/sec";
const files = fs.readdirSync(dir).filter(f => f.endsWith(".js")).sort();

const posCount = {};       // 现有 POS 标签 -> 出现次数
const verbInf = {};        // 动词原形 -> { pos:Set, count, example }
let totalRows = 0, verbRows = 0, nounRows = 0, adjRows = 0;

function normPOS(p){ return String(p||"").trim().toLowerCase().replace(/\.+$/,"").replace(/\.+/g,"."); }

for (const f of files) {
  const code = fs.readFileSync(dir + "/" + f, "utf8");
  const sandbox = { window: { BOOK_DATA: [] } };
  vm.runInNewContext(code, sandbox);
  const arr = sandbox.window.BOOK_DATA;
  if (!arr) continue;
  for (const g of arr) {
    if (!g || !g.secs) continue;
    for (const sec of g.secs) {
      for (const key of ["w","s","e"]) {
        const row = sec[key];
        if (!row) continue;
        for (const item of row) {
          if (!Array.isArray(item) || item.length < 3) continue;
          const it = String(item[1] || "").trim();
          const posRaw = String(item[2] || "").trim();
          if (!posRaw) continue;
          totalRows++;
          posCount[posRaw] = (posCount[posRaw] || 0) + 1;
          const np = normPOS(posRaw);
          const isNoun = ["n","s","n.m","s.m","n.f","s.f","m","f","nm","nf","名","noun"].includes(np);
          const isAdj = ["agg","adj","形","aggettivo"].includes(np);
          const isVerb = np.startsWith("v") || np === "i" || np.startsWith("v.");
          if (isNoun) nounRows++;
          if (isAdj) adjRows++;
          if (isVerb) {
            verbRows++;
            // 取动词原形：短语取首词；反身去掉 si/rsi/arsi...
            let inf = it.split(/\s+/)[0].toLowerCase();
            inf = inf.replace(/(si|rsi|arsi|irsi|ersi)$/,"").replace(/[^a-zàèéìòù]/g,"");
            if (!inf) inf = it.toLowerCase();
            if (!verbInf[inf]) verbInf[inf] = { pos: new Set(), count: 0, example: it };
            verbInf[inf].pos.add(posRaw);
            verbInf[inf].count++;
          }
        }
      }
    }
  }
}

const posKeys = Object.keys(posCount).sort((a,b)=>posCount[b]-posCount[a]);
console.log("=== 现有 POS 标签分布（全站）===");
console.log("总行数:", totalRows, "| 名词行:", nounRows, "| 形容词行:", adjRows, "| 动词行:", verbRows);
console.log("不同 POS 标签数:", posKeys.length);
for (const k of posKeys) console.log("  " + JSON.stringify(k).padEnd(14), posCount[k]);

const verbs = Object.keys(verbInf).sort();
console.log("\n=== 不同动词原形数:", verbs.length, "===");
let out = "";
for (const v of verbs) {
  const o = verbInf[v];
  out += v + "\t" + o.count + "\t" + [...o.pos].join("|") + "\t" + o.example + "\n";
}
fs.writeFileSync("tools/_pos_verbs.txt", out);
console.log("动词原形清单已写入 tools/_pos_verbs.txt （" + verbs.length + " 个）");
