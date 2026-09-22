/* 修复 sec 文件缺失的 window.BOOK_DATA 初始化守卫。
 * 浏览器加载 data/sec/N.js 时执行 window.BOOK_DATA[N]=...，
 * 若 window.BOOK_DATA 未初始化会抛错，导致整页数据加载失败。
 * 此脚本确保每个 sec 文件以 "window.BOOK_DATA=window.BOOK_DATA||{};" 开头（仅缺失时补）。
 */
const fs = require("fs");
const path = require("path");
const dir = path.join(__dirname, "..", "data", "sec");
const GUARD = "window.BOOK_DATA=window.BOOK_DATA||{};";
const files = fs.readdirSync(dir).filter(f => f.endsWith(".js")).sort();
let fixed = 0, ok = 0, err = 0;
for (const f of files) {
  const fp = path.join(dir, f);
  let s;
  try { s = fs.readFileSync(fp, "utf8"); } catch (e) { console.log("READ ERR", f, e.message); err++; continue; }
  if (s.startsWith(GUARD)) { ok++; continue; }
  // 文件应以 window.BOOK_DATA[ 开头（无守卫）
  fs.writeFileSync(fp, GUARD + s);
  fixed++;
  console.log("已补齐守卫:", f);
}
console.log(`\n完成 | 补齐:${fixed} | 原本已有:${ok} | 读取错误:${err}`);

// 校验：在空 window 下执行，确认 window.BOOK_DATA[N] 能被赋值
let vmErr = 0;
for (const f of files) {
  const code = fs.readFileSync(path.join(dir, f), "utf8");
  const sb = { window: {} };
  try { require("vm").runInNewContext(code, sb); }
  catch (e) { console.log("VM ERR", f, e.message); vmErr++; }
  const gid = parseInt(f.replace(/\.js$/, ""), 10);
  if (sb.window.BOOK_DATA == null) { console.log("GUARD MISSING after fix:", f); vmErr++; }
  else if (sb.window.BOOK_DATA[gid] == null) { console.log("DATA MISSING:", f); vmErr++; }
}
console.log(vmErr === 0 ? "校验通过：所有文件在空 window 下可正确挂载 BOOK_DATA" : `校验失败：${vmErr} 处`);
