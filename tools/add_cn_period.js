// 为全站「例句」(s 数组) 的中文长句补齐中文句号「。」
// s 行结构: [意语句, 中文句, "", it音频, zh音频, 拼音, ""]
// e/w 数组为词汇释义(中位长度2字)，不是句子，不处理。
// 用法: node tools/add_cn_period.js scan   |   node tools/add_cn_period.js apply
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.dirname(__dirname);
const SECDIR = path.join(ROOT, 'data', 'sec');
const MODE = process.argv[2] || 'scan';

const TERMINAL = new Set(['。', '！', '？', '!', '?', '…', '；', ';']);
const CJK = /[\u4e00-\u9fff]/;

function load(fp) {
  const code = fs.readFileSync(fp, 'utf8');
  const ctx = { window: {} };
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  const gids = Object.keys(ctx.window.BOOK_DATA);
  if (gids.length !== 1) throw new Error(`${fp}: 期望 1 个 gid，实际 ${gids.length}`);
  return { gid: gids[0], obj: ctx.window.BOOK_DATA[gids[0]], code };
}

// 保留原文件的行尾 (CRLF / LF)
function lineEnding(code) {
  if (code.endsWith('\r\n')) return '\r\n';
  if (code.endsWith('\n')) return '\n';
  return '';
}

function serialize(gid, obj, ending) {
  return `window.BOOK_DATA=window.BOOK_DATA||{};window.BOOK_DATA[${gid}]=${JSON.stringify(obj)};${ending}`;
}

let files = 0, total = 0, fixed = 0, already = 0, skippedFiles = 0, changedFiles = 0;
const touched = [];

for (const name of fs.readdirSync(SECDIR).filter(f => f.endsWith('.js')).sort((a, b) => (+a.replace('.js', '')) - (+b.replace('.js', '')))) {
  const fp = path.join(SECDIR, name);
  const { gid, obj, code } = load(fp);
  files++;
  const ending = lineEnding(code);

  // 保真校验：未改动时重建必须与原文逐字节一致
  if (serialize(gid, obj, ending) !== code) {
    console.log(`!! ${name}: 序列化与原文件不一致，跳过`);
    skippedFiles++;
    continue;
  }

  let changed = false;
  for (const sec of obj.secs) {
    for (const row of (sec.s || [])) {
      if (!Array.isArray(row)) continue;
      const cn = row[1];
      if (typeof cn !== 'string' || cn.length === 0) continue;
      if (!CJK.test(cn)) continue;          // 非中文不处理（防御性）
      total++;
      if (TERMINAL.has(cn[cn.length - 1])) { already++; continue; }
      row[1] = cn + '。';
      fixed++;
      changed = true;
    }
  }

  if (changed) {
    changedFiles++;
    touched.push(name);
    if (MODE === 'apply') fs.writeFileSync(fp, serialize(gid, obj, ending), 'utf8');
  }
}

console.log(`文件=${files}  例句总数=${total}  已有句末标点=${already}  需补句号=${fixed}  涉及文件=${changedFiles}`);
console.log(MODE === 'apply' ? '已写入。' : '(scan 模式，未写入)');
if (skippedFiles) console.log(`跳过文件=${skippedFiles}`);
