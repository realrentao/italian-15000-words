// 全站词性短码规范化：Nm/Nf/Agg/Va/Ve/Va·Ve + 扩展短码
// 用法：node tools/pos_normalize.js          (dry-run，只统计+产出核对清单)
//      APPLY=1 node tools/pos_normalize.js    (真正写入 sec 文件)
const fs = require("fs");
const vm = require("vm");
const APPLY = process.env.APPLY === "1";
const dir = "data/sec";
const files = fs.readdirSync(dir).filter(f => f.endsWith(".js")).sort();

// ---- 助动词 essere 动词表（核心、无争议；其余默认 avere，靠核对清单兜底）----
const ESSERE = new Set(["andare","venire","stare","essere","rimanere","restare","diventare","divenire",
  "nascere","morire","tornare","ritornare","partire","arrivare","entrare","uscire","salire","scendere",
  "cadere","ricadere","riuscire","parere","sembrare","apparire","scomparire","comparire","sparire",
  "succedere","accadere","avvenire","capitare","scappare","intervenire","sopravvivere","rinascere",
  "sovraggiungere","sopraggiungere","pervenire","piacere","dispiacere","bisognare","occorrere",
  "giacere","soggiornare","tramontare","vagare","zoppicare","ringiovanire","fiorire","appassire",
  "marcre","marcire","perire","sfiorire","svanire","trasalire","vibrare","stancarsi","stupire",
  "arrendersi","assopirsi","avverarsi","estinguersi","inverdire","languire","logorarsi","penzolare",
  "prosperare","quietarsi","rinverdire","rinvigorire","rintontirsi","rinvenire","smaltire","smarrire",
  "stremarsi","svolgersi","trasecolare","trascinare","vacillare","vaneggiare"]);

// ---- 双助动词（avere/essere 皆可，取 Va/Ve）----
const BOTH = new Set(["crescere","diminuire","aumentare","calare"]);

// 希腊-origin 阳性以 -ma 结尾（problema/sistema...）
const MALE_MA = /ma$/;
// 以 -a 结尾却是阳性的名词（少数例外）
const MALE_A_EXC = new Set(["poeta","pirata","atleta","idiota","egoista","ipocrita","programma","sistema",
  "clima","dramma","poema","schema","tema","cinema","idioma","dogma","lemma","telegramma","diagramma",
  "enigma","trauma","pigiama","panorama","carisma","aroma","plasma","stigma","dilemma"]);
// 以 -o 结尾却是阴性的名词（少数例外）
const FEMALE_O_EXC = new Set(["mano","radio","auto","foto","libido","bio","dinamo","eco","metro","cronometro","ipotesi","tisi"]);

function guessGender(word) {
  let w = String(word || "").toLowerCase().replace(/[^a-zàèéìòù]/g, "").trim();
  if (!w) return { g: "N", conf: "no-it" };
  // 复合名词取最后一个词
  const parts = w.split(/\s+/);
  w = parts[parts.length - 1];
  if (w.endsWith("ù") || w.endsWith("à")) return { g: "Nf", conf: "hi" };
  if (MALE_MA.test(w)) return { g: "Nm", conf: "hi" };        // 希腊-origin 多阳性 (ends ma)
  if (MALE_A_EXC.has(w)) return { g: "Nm", conf: "hi" };      // 以-a结尾的阳性例外
  if (w.endsWith("a")) return { g: "Nf", conf: "hi" };
  if (FEMALE_O_EXC.has(w)) return { g: "Nf", conf: "hi" };    // 以-o结尾的阴性例外
  if (w.endsWith("o")) return { g: "Nm", conf: "hi" };
  if (w.endsWith("e") || w.endsWith("i")) return { g: "N", conf: "maybe" }; // -e/-i 性别不定
  return { g: "N", conf: "maybe" };
}

function isReflexive(it) {
  return /(si|rsi|arsi|irsi|ersi|arsi)$/.test(String(it||"").toLowerCase().split(/\s+/)[0]);
}

function verbInf(it) {
  let inf = String(it || "").toLowerCase().split(/\s+/)[0].replace(/(si|rsi|arsi|irsi|ersi)$/,"").replace(/[^a-zàèéìòù]/g,"");
  return inf;
}

// 返回 { cat, newPos, flag }
function classify(posRaw, itWord, rowKey) {
  const raw = String(posRaw || "").trim();
  const low = raw.toLowerCase();
  const has = (s) => low.includes(s);

  // ---- 形容词（优先于名词，因 "agg.m" 等含 m）----
  if (has("形") || has("agg") || has("adj") || /^a(\(|\.|$)/.test(low) || has("a(m)") || has("a.(m)")) {
    return { cat: "adj", newPos: "Agg", flag: "" };
  }
  // ---- 副词 ----
  if (has("副") || has("avv") || has("adv")) return { cat: "adv", newPos: "Avv", flag: "" };
  // ---- 介词 ----
  if (has("介") || has("prep") || has("prép")) return { cat: "prep", newPos: "Prep", flag: "" };
  // ---- 连词 ----
  if (has("连") || has("cong")) return { cat: "cong", newPos: "Cong", flag: "" };
  // ---- 冠词 ----
  if (has("冠") || has("art")) return { cat: "art", newPos: "Art", flag: "" };
  // ---- 代词 ----
  if (has("代") || has("pron") || low === "pr.") return { cat: "pron", newPos: "Pron", flag: "" };
  // ---- 叹词 ----
  if (has("叹") || has("inter") || has("escl")) return { cat: "inter", newPos: "Inter", flag: "" };
  // ---- 短语/固定搭配 ----
  if (has("短") || has("固") || has("loc")) {
    if (has("动")) return { cat: "verb", newPos: verbAux(itWord, raw), flag: "loc-v" };
    return { cat: "loc", newPos: "Loc", flag: "" };
  }
  // ---- 不变格 ----
  if (has("inv")) return { cat: "inv", newPos: "Inv", flag: "" };
  // ---- 复数 ----
  if (low === "pl." || has("pl")) return { cat: "pl", newPos: "Pl", flag: "" };

  // ---- 动词 ----
  const verbish = has("动") || low.startsWith("v") || low === "i" || low === "i." || low === "t." ||
                  low === "vt" || low === "r." || /^v[\.]/ .test(low);
  if (verbish) {
    const aux = verbAux(itWord, raw);
    return { cat: "verb", newPos: aux, flag: (aux === "Va" ? "def-a" : "") };
  }

  // ---- 名词 ----
  if (has("名") || has("n.") || has("s.") || has("n") || has("s") || has("m.") || has("f.") || /^[nmfs]\b/.test(low)) {
    const male = /(^|[^a-z])m\./.test(low) || has("m.pl") || has("m.") || has("名 m") || low === "m" || low === "m.inv" || has("agg.m");
    const female = /(^|[^a-z])f\./.test(low) || has("f.pl") || has("f.") || has("名 f") || low === "f" || low === "f.inv" || has("agg.f");
    if (male && female) return { cat: "noun", newPos: "Nm/Nf", flag: "amb-gender" };
    if (male) return { cat: "noun", newPos: "Nm", flag: "" };
    if (female) return { cat: "noun", newPos: "Nf", flag: "" };
    // 无性别标记
    const g = guessGender(itWord);
    if (g.g === "N") return { cat: "noun", newPos: "N", flag: "guess-" + g.conf + ":it=" + String(itWord||"") };
    return { cat: "noun", newPos: g.g, flag: "guess-" + g.conf };
  }

  // 无法识别（剧名等脏数据）
  return { cat: "unknown", newPos: null, flag: "junk:" + raw };
}

function verbAux(itWord, raw) {
  // 反身/代词式动词（v.rifl / v.pr / 词形以 -si 结尾）→ 用 essere
  if (/rifl|pr\.|反身|身|pron|v\.r/i.test(raw)) return "Ve";
  if (isReflexive(itWord)) return "Ve";
  const inf = verbInf(itWord);
  if (BOTH.has(inf)) return "Va/Ve";
  if (ESSERE.has(inf)) return "Ve";
  if (/(si|rsi|arsi|irsi|ersi)$/.test(inf)) return "Ve";
  return "Va";
}

// ---- 主流程 ----
let changed = 0, total = 0;
const newDist = {};
const reviewNoun = [];   // 性别推断待核对
const reviewVerb = [];   // 动词助动词
const reviewUnknown = []; // 未识别
const reviewAmb = [];     // 性别歧义

for (const f of files) {
  const code = fs.readFileSync(dir + "/" + f, "utf8");
  const sb = { window: { BOOK_DATA: [] } };
  vm.runInNewContext(code, sb);
  const arr = sb.window.BOOK_DATA;
  if (!arr) continue;
  let fileChanged = false;
  for (const g of arr) {
    if (!g || !g.secs) continue;
    for (const sec of g.secs) {
      for (const key of ["w","s","e"]) {
        const row = sec[key];
        if (!row) continue;
        for (const item of row) {
          if (!Array.isArray(item) || item.length < 3) continue;
          const raw = String(item[2] || "").trim();
          if (!raw) continue;
          const it = item[1];
          const r = classify(raw, it, key);
          total++;
          if (r.cat === "unknown") {
            if (APPLY) item[2] = ""; else item[2] = raw; // dry-run 不动
            reviewUnknown.push([f, key, raw, String(it||"")]);
            fileChanged = true; changed++;
            continue;
          }
          if (r.newPos === null) { reviewUnknown.push([f,key,raw,String(it||"")]); continue; }
          // 可识别词性（w/s/e 统一改写）；unknown 已在上文清空
          if (item[2] !== r.newPos) {
            if (APPLY) item[2] = r.newPos;
            fileChanged = true; changed++;
          }
          // 收集核对项
          if (r.cat === "noun" && (r.flag.startsWith("guess") || r.flag === "amb-gender")) {
            if (r.flag === "amb-gender") reviewAmb.push([f, String(it||""), raw, r.newPos]);
            else reviewNoun.push([f, String(it||""), raw, r.newPos, r.flag]);
          }
          if (r.cat === "verb") {
            reviewVerb.push([String(it||""), raw, r.newPos, r.flag]);
          }
          newDist[r.newPos] = (newDist[r.newPos] || 0) + 1;
        }
      }
    }
  }
  if (APPLY && fileChanged) {
    // 重新序列化：保持原格式 window.BOOK_DATA[gid]={...}; 单行 JSON
    const out = "window.BOOK_DATA=window.BOOK_DATA||{};\n" +
      arr.filter(Boolean).map(g => "window.BOOK_DATA[" + g.gid + "]=" + JSON.stringify(g) + ";").join("\n") + "\n";
    fs.writeFileSync(dir + "/" + f, out);
  }
}

// 汇总
console.log("模式:", APPLY ? "APPLY(写入)" : "DRY-RUN", "| 处理行:", total, "| 改动:", changed);
console.log("性别推断待核对(名词):", reviewNoun.length, "| 性别歧义:", reviewAmb.length, "| 动词核对:", reviewVerb.length, "| 未识别/清空:", reviewUnknown.length);
console.log("--- 改写后新词性分布 ---");
const nd = Object.keys(newDist).sort((a,b)=>newDist[b]-newDist[a]);
for (const k of nd) console.log("  " + String(k).padEnd(8), newDist[k]);

fs.writeFileSync("tools/_review_noun_gender.txt", reviewNoun.map(r=>r.join("\t")).join("\n") + "\n");
fs.writeFileSync("tools/_review_noun_amb.txt", reviewAmb.map(r=>r.join("\t")).join("\n") + "\n");
fs.writeFileSync("tools/_review_verb.txt", reviewVerb.map(r=>r.join("\t")).join("\n") + "\n");
fs.writeFileSync("tools/_review_unknown.txt", reviewUnknown.map(r=>r.join("\t")).join("\n") + "\n");
console.log("核对清单已写入 tools/_review_*.txt");
