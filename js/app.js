/* ===== 意大利语单词随身背 · 互动学习站 ===== */
(function () {
  "use strict";

  var META = window.BOOK_META || { title: "", author: "", grupos: [], totalAll: 0 };
  var DATA = {};            // gid -> 分册数据
  var AUDIO = "audio/";
  var LS_DONE = "sv15000_done", LS_THEME = "sv15000_theme", LS_POS = "sv15000_pos";
  var LS_SRS = "sv15000_srs";
  var SRS_INT = [0, 10 * 60 * 1000, 60 * 60 * 1000, 864e5, 3 * 864e5, 7 * 864e5];
  var study = { active: false, mode: "card", scope: "sec", items: [], i: 0, total: 0,
                known: 0, unknown: 0, cur: null, dueOnly: false, srs: {} };

  var state = { g: 0, p: 0, s: 0, done: {}, theme: "light" };
  var FLAT = [];            // 全局 Parte 顺序 [{g,p,gid,no,name}]
  var el = function (id) { return document.getElementById(id); };

  /* 词性 → 中文（同时覆盖意语缩写 m./f./n.f./v.t./adj./inv. 与原笔记直接写的中文 形/名/介/副/固/短） */
  var POS_ZH = {
    "n":"名词","s":"名词","m":"阳性名词","f":"阴性名词",
    "n.m":"阳性名词","n.f":"阴性名词","s.m":"阳性名词","s.f":"阴性名词",
    "adj":"形容词","agg":"形容词",
    "v":"动词","v.t":"及物动词","v.i":"不及物动词",
    "v.tr":"及物动词","v.intr":"不及物动词","v.rifl":"反身动词","i":"不及物动词",
    "avv":"副词","adv":"副词","prep":"介词","cong":"连词",
    "art":"冠词","pron":"代词","inter":"叹词","escl":"感叹词","loc":"短语","pl":"复数","inv":"不变",
    "形":"形容词","名":"名词","介":"介词","副":"副词","固":"固定搭配","短":"短语"
  };
  function posZh(p) {
    if (!p) return "";
    function look(s) {
      if (POS_ZH[s] != null) return POS_ZH[s];
      var t = s.replace(/\.+$/, ""); if (POS_ZH[t] != null) return POS_ZH[t];
      var k = s.replace(/\./g, "").toLowerCase(); if (POS_ZH[k] != null) return POS_ZH[k];
      return null;
    }
    function one(tok) {
      tok = tok.trim();
      var a = look(tok); if (a) return a;
      if (tok.indexOf(".") >= 0) {
        var mp = tok.split(".").filter(Boolean).map(look);
        if (mp.length && mp.every(function (m) { return m != null; })) return mp.join("·");
      }
      return tok;
    }
    return p.trim().split(/\s+/).map(one).join("·");
  }
  var content = el("content");

  function buildFlat() {
    FLAT = [];
    META.grupos.forEach(function (gr, gi) {
      gr.partes.forEach(function (pt, pi) {
        FLAT.push({ g: gi, p: pi, gid: pt.gid, no: pt.no, name: pt.name });
      });
    });
  }
  function curParte() { return META.grupos[state.g].partes[state.p]; }
  function curSec() { return curParte().secs[state.s]; }
  function esc(t) {
    return String(t == null ? "" : t).replace(/&/g, "&amp;")
      .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ---------- localStorage ---------- */
  function loadLS() {
    try { state.done = JSON.parse(localStorage.getItem(LS_DONE) || "{}"); } catch (e) { state.done = {}; }
    state.theme = localStorage.getItem(LS_THEME) || "light";
    document.documentElement.setAttribute("data-theme", state.theme);
    try {
      var pos = JSON.parse(localStorage.getItem(LS_POS) || "null");
      if (pos && META.grupos.length) {
        state.g = pos.g || 0; state.p = pos.p || 0; state.s = pos.s || 0;
        if (!META.grupos[state.g]) { state.g = 0; state.p = 0; state.s = 0; }
        else if (!META.grupos[state.g].partes[state.p]) { state.p = 0; state.s = 0; }
        else if (!curParte().secs[state.s]) state.s = 0;
      }
    } catch (e) { }
  }
  function saveDone() { try { localStorage.setItem(LS_DONE, JSON.stringify(state.done)); } catch (e) { } }
  function savePos() { try { localStorage.setItem(LS_POS, JSON.stringify({ g: state.g, p: state.p, s: state.s })); } catch (e) { } }

  /* ---------- 数据加载 ---------- */
  function loadParte(gid, cb) {
    if (DATA[gid]) { cb(DATA[gid]); return; }
    var s = document.createElement("script");
    s.src = "data/sec/" + gid + ".js";
    s.onload = function () {
      var d = (window.BOOK_DATA || {})[gid] || null;
      if (d) DATA[gid] = d;
      s.remove(); cb(d);
    };
    s.onerror = function () { s.remove(); cb(null); };
    document.head.appendChild(s);
  }
  function loadAll(cb) {
    var rest = FLAT.filter(function (f) { return !DATA[f.gid]; });
    if (!rest.length) { cb(); return; }
    var n = rest.length;
    rest.forEach(function (f) {
      loadParte(f.gid, function () { if (--n <= 0) cb(); });
    });
  }

  /* ---------- 目录（篇 → Parte → Sección） ---------- */
  function renderToc() {
    var toc = el("toc"), h = "";
    META.grupos.forEach(function (gr, gi) {
      var openG = (gi === state.g);
      var dn = gr.partes.filter(function (pt) {
        return pt.secs.filter(function (s) { return state.done[pt.gid + "-" + s.no]; }).length;
      }).length;
      h += '<div class="grupo' + (openG ? " open" : "") + '" data-g="' + gi + '">'
        + '<div class="grupo-hd" data-g="' + gi + '"><span class="caret">▶</span>'
        + '<span class="gname">' + esc(gr.name) + '</span>'
        + '<span class="gcount">' + gr.partes.length + '</span></div><div class="parte-list">';
      gr.partes.forEach(function (pt, pi) {
        var openP = openG && pi === state.p;
        h += '<div class="parte-item' + (openP ? " open" : "") + '" data-g="' + gi + '" data-p="' + pi + '">'
          + '<div class="parte-hd" data-g="' + gi + '" data-p="' + pi + '">'
          + '<span class="caret">▶</span><span class="pno">' + pt.no + '</span>'
          + '<span class="pname">' + esc(pt.name) + '</span></div><div class="sec-list">';
        pt.secs.forEach(function (s, si) {
          var act = (gi === state.g && pi === state.p && si === state.s);
          h += '<div class="sec-item' + (act ? " active" : "") + '" data-g="' + gi
            + '" data-p="' + pi + '" data-s="' + si + '">'
            + '<span class="sno">' + s.no + '</span>'
            + '<span class="sname">' + esc(s.name) + '</span>'
            + (state.done[pt.gid + "-" + s.no] ? '<span class="sdot"></span>' : '')
            + '</div>';
        });
        h += '</div></div>';
      });
      h += '</div></div>';
    });
    toc.innerHTML = h;
    var nv = FLAT.length;
    var ns = 0, nd = 0;
    META.grupos.forEach(function (gr) {
      gr.partes.forEach(function (pt) {
        ns += pt.secs.length;
        pt.secs.forEach(function (s) { if (state.done[pt.gid + "-" + s.no]) nd++; });
      });
    });
    el("sideCount").textContent = META.grupos.length + " 篇 · " + nv + " 大类 · " + ns
      + " 小节 · 已学 " + nd;
  }

  /* ---------- 内容 ---------- */
  function render() {
    var pm = curParte(), sm = curSec();
    if (!pm || !sm) return;
    loadParte(pm.gid, function (d) {
      if (!d) { content.innerHTML = '<div class="empty">加载失败</div>'; return; }
      var sec = null;
      for (var i = 0; i < d.secs.length; i++) if (d.secs[i].no === sm.no) sec = d.secs[i];
      if (!sec) { content.innerHTML = '<div class="empty">未找到该小节</div>'; return; }

      var gr = META.grupos[state.g];
      var key = pm.gid + "-" + sm.no, isDone = !!state.done[key];
      var h = '<div class="crumb">' + esc(gr.name) + ' › Parte ' + pm.no
        + ' <b>' + esc(pm.name) + '</b> · Sección ' + sm.no + '</div>'
        + '<h1 class="sec-title">' + esc(sm.name) + '</h1>'
        + '<div class="sec-meta"><span>终极分类词 ' + sec.w.length + '</span>'
        + '<span>经典实用句 ' + sec.s.length + '</span>'
        + '<span>词汇大拓展 ' + sec.e.length + '</span>'
        + '<button class="btn-done' + (isDone ? " on" : "") + '" id="doneBtn">'
        + (isDone ? "✓ 已学完" : "标记学完") + '</button></div>'
        + navRow();

      if (sec.w.length) h += block("终极分类词", "w", sec.w);
      if (sec.s.length) h += blockSent(sec.s);
      if (sec.e.length) h += block("词汇大拓展", "e", sec.e);
      if (!sec.w.length && !sec.s.length && !sec.e.length)
        h += '<div class="empty">本节内容待补充 —— 在 <code>data/sec/'
          + pm.gid + '.js</code> 的对应小节里填入 w（终极分类词）/ s（经典实用句）/ e（词汇大拓展）即可显示。</div>';

      content.innerHTML = h;
      window.scrollTo(0, 0);
      bindContent();
      stopPlay();
      renderToc();
    });
  }

  function navRow() {
    var prev = '<button data-nav="prev">← 上一节</button>';
    var next = '<button data-nav="next">下一节 →</button>';
    var fi = flatIndex();
    if (fi <= 0 && state.s <= 0) prev = '<button disabled>← 上一节</button>';
    if (fi >= FLAT.length - 1 && state.s >= curParte().secs.length - 1)
      next = '<button disabled>下一节 →</button>';
    return '<div class="nav-row">' + prev + next + '</div>';
  }
  function flatIndex() {
    for (var i = 0; i < FLAT.length; i++)
      if (FLAT[i].g === state.g && FLAT[i].p === state.p) return i;
    return 0;
  }

  function block(title, kind, arr) {
    var gid = curParte().gid, sno = curSec().no;
    var h = '<div class="block"><div class="block-hd"><h3>' + title + '</h3>'
      + '<span class="tag">' + arr.length + '</span>'
      + '<button class="mini-play" data-playblock="' + kind + '">▶ 连播本组</button></div>';
    arr.forEach(function (it, i) {
      var id = uid(gid, sno, kind, i);
      h += '<div class="row" id="' + id + '"><span class="idx">' + (i + 1) + '</span>'
        + '<div class="body"><div class="line-es">'
        + '<span class="es" data-a="' + AUDIO + it[3] + '">' + esc(it[1]) + '</span>'
        + (it[6] ? '<span class="ipa pron" title="意语音标">/' + esc(it[6]) + '/</span>' : '')
        + '<span class="pos">' + esc(it[2]) + '</span></div>'
        + '<div class="zh" data-a="' + AUDIO + it[4] + '">' + esc(it[0])
        + (it[2] ? ' <span class="pos pos-zh">' + esc(posZh(it[2])) + '</span>' : '')
        + '</div>'
        + (it[5] ? '<div class="py pron">' + esc(it[5]) + '</div>' : '')
        + '</div>'
        + '<button class="spk" data-a="' + AUDIO + it[3] + '" title="意语发音">🔊</button>'
        + '<button class="spk" data-a="' + AUDIO + it[4] + '" title="中文发音">汉</button></div>';
    });
    return h + '</div>';
  }

  function blockSent(arr) {
    var gid = curParte().gid, sno = curSec().no, kind = "s";
    var h = '<div class="block"><div class="block-hd"><h3>经典实用句</h3>'
      + '<span class="tag">' + arr.length + '</span>'
      + '<button class="mini-play" data-playblock="' + kind + '">▶ 连播本组</button></div>';
    arr.forEach(function (it, i) {
      var id = uid(gid, sno, kind, i);
      h += '<div class="sent" id="' + id + '">'
        + '<div class="s-es" data-a="' + AUDIO + it[3] + '">' + esc(it[0]) + '</div>'
        + (it[6] ? '<div class="s-ipa pron">/' + esc(it[6]) + '/</div>' : '')
        + '<div class="s-zh" data-a="' + AUDIO + it[4] + '">' + esc(it[1]) + '</div>'
        + (it[5] ? '<div class="s-py pron">' + esc(it[5]) + '</div>' : '')
        + (it[2] ? '<div class="s-src">' + esc(it[2]) + '</div>' : '') + '</div>';
    });
    return h + '</div>';
  }

  function uid(gid, sno, kind, i) { return "u" + gid + "_" + sno + "_" + kind + "_" + i; }

  function bindContent() {
    var db = el("doneBtn");
    if (db) db.onclick = function () {
      var k = curParte().gid + "-" + curSec().no;
      if (state.done[k]) delete state.done[k]; else state.done[k] = 1;
      saveDone(); render();
    };
    content.querySelectorAll("[data-nav]").forEach(function (b) {
      b.onclick = function () { navigate(b.getAttribute("data-nav")); };
    });
    content.querySelectorAll(".mini-play").forEach(function (b) {
      b.onclick = function () {
        var kind = b.getAttribute("data-playblock");
        buildUnits("sec", function () {
          P.units = P.units.filter(function (u) { return u.kind === kind; });
          P.dirty = true; expand(); doStart();
        });
      };
    });
  }

  function navigate(dir) {
    if (dir === "prev") {
      if (state.s > 0) state.s--;
      else {
        var fi = flatIndex();
        if (fi > 0) { var pv = FLAT[fi - 1]; state.g = pv.g; state.p = pv.p; state.s = META.grupos[pv.g].partes[pv.p].secs.length - 1; }
        else return;
      }
    } else {
      if (state.s < curParte().secs.length - 1) state.s++;
      else {
        var fi2 = flatIndex();
        if (fi2 < FLAT.length - 1) { var nx = FLAT[fi2 + 1]; state.g = nx.g; state.p = nx.p; state.s = 0; }
        else return;
      }
    }
    savePos(); render();
  }

  /* ================= 播放引擎 ================= */
  var P = {
    units: [], list: [], i: 0, playing: false, dirty: true,
    players: [new Audio(), new Audio()],
    pre: null, cur: 0, timer: null, busy: false, err: 0
  };

  function rate() { return parseFloat(el("rateSel").value) || 1; }
  function gapMs() { return parseInt(el("gapSel").value, 10) || 0; }
  function loopOn() { return el("loopChk").checked; }
  function mode() { return el("modeSel").value; }

  function unitsOf(gid, sec) {
    var out = [];
    sec.w.forEach(function (it, i) {
      out.push({ id: uid(gid, sec.no, "w", i), kind: "w", es: it[1], zh: it[0], ae: it[3], az: it[4] });
    });
    sec.s.forEach(function (it, i) {
      out.push({ id: uid(gid, sec.no, "s", i), kind: "s", es: it[0], zh: it[1], ae: it[3], az: it[4] });
    });
    sec.e.forEach(function (it, i) {
      out.push({ id: uid(gid, sec.no, "e", i), kind: "e", es: it[1], zh: it[0], ae: it[3], az: it[4] });
    });
    return out;
  }

  function collect(scope, cb) {
    if (scope === "sec") {
      loadParte(curParte().gid, function (d) {
        if (!d) { cb([]); return; }
        var sno = curSec().no, sec = null;
        for (var i = 0; i < d.secs.length; i++) if (d.secs[i].no === sno) sec = d.secs[i];
        cb(sec ? unitsOf(curParte().gid, sec) : []);
      });
    } else if (scope === "parte") {
      loadParte(curParte().gid, function (d) {
        if (!d) { cb([]); return; }
        var out = [];
        d.secs.forEach(function (s) { out = out.concat(unitsOf(d.gid, s)); });
        cb(out);
      });
    } else {
      loadAll(function () {
        var out = [];
        FLAT.forEach(function (f) {
          var d = DATA[f.gid]; if (!d) return;
          d.secs.forEach(function (s) { out = out.concat(unitsOf(f.gid, s)); });
        });
        cb(out);
      });
    }
  }

  function expand() {
    var m = mode(), L = [];
    if (m === "it-zh") {
      P.units.forEach(function (u) {
        L.push({ src: AUDIO + u.ae, uid: u.id, lang: "it" });
        L.push({ src: AUDIO + u.az, uid: u.id, lang: "zh" });
      });
    } else if (m === "all-it-zh") {
      P.units.forEach(function (u) { L.push({ src: AUDIO + u.ae, uid: u.id, lang: "it" }); });
      P.units.forEach(function (u) { L.push({ src: AUDIO + u.az, uid: u.id, lang: "zh" }); });
    } else if (m === "it-only") {
      P.units.forEach(function (u) { L.push({ src: AUDIO + u.ae, uid: u.id, lang: "it" }); });
    } else {
      P.units.forEach(function (u) { L.push({ src: AUDIO + u.az, uid: u.id, lang: "zh" }); });
    }
    P.list = L; P.i = 0;
  }

  function buildUnits(scope, cb) { collect(scope, function (u) { P.units = u; if (cb) cb(); }); }

  function updateProgress() {
    var it = P.list[P.i];
    if (!it || !P.units.length) { el("plLabel").textContent = "未播放"; el("plBar").style.width = "0%"; return; }
    var ui = 0;
    for (var k = 0; k < P.units.length; k++) if (P.units[k].id === it.uid) { ui = k; break; }
    el("plBar").style.width = ((P.i + 1) / P.list.length * 100).toFixed(1) + "%";
    el("plLabel").textContent = "第 " + (ui + 1) + "/" + P.units.length + " 条 · "
      + (it.lang === "it" ? "意语" : "中文");
  }

  function highlight(uidStr) {
    clearHL();
    var t = document.getElementById(uidStr);
    if (!t) return;
    t.classList.add("cur");
    var r = t.getBoundingClientRect();
    if (r.top < 90 || r.bottom > window.innerHeight - 130) {
      try { t.scrollIntoView({ block: "center", behavior: "smooth" }); } catch (e) { }
    }
  }
  function clearHL() {
    var old = document.querySelectorAll(".cur");
    for (var i = 0; i < old.length; i++) old[i].classList.remove("cur");
  }

  function preloadNext() {
    var nx = P.list[P.i + 1];
    if (!nx) return;
    try {
      if (!P.pre) P.pre = new Audio();
      P.pre.preload = "auto";
      P.pre.src = nx.src;      // 独立对象，不绑定任何回调
    } catch (e) { }
  }

  function step() {
    if (!P.playing) return;
    if (P.i >= P.list.length) {
      if (loopOn()) P.i = 0; else { stopPlay(true); return; }
    }
    var it = P.list[P.i];
    if (!it) { stopPlay(true); return; }
    var a = P.players[P.cur];
    P.busy = false;
    try { a.pause(); } catch (e) { }
    a.src = it.src;
    a.playbackRate = rate();
    a.onended = function () { if (P.busy) return; P.busy = true; advance(); };
    a.onerror = function () { P.err++; if (P.busy) return; P.busy = true; advance(); };
    var pr = a.play();
    if (pr && pr.catch) pr.catch(function () { if (!P.busy) { P.busy = true; advance(); } });
    highlight(it.uid);
    updateProgress();
    preloadNext();
  }

  function advance() {
    P.i++; P.cur ^= 1;
    clearTimeout(P.timer);
    P.timer = setTimeout(step, gapMs());
  }

  function doStart() {
    if (!P.list.length) return;
    if (P.i >= P.list.length) P.i = 0;
    P.playing = true;
    el("playBtn").classList.add("playing");
    clearTimeout(P.timer);
    step();
  }

  function startPlay() {
    if (P.dirty || !P.list.length) {
      var sc = el("scopeSel").value;
      el("plLabel").textContent = sc === "all" ? "正在准备全书播放…"
        : sc === "parte" ? "正在准备本大类播放…" : "准备中…";
      buildUnits(sc, function () { P.dirty = false; expand(); doStart(); });
    } else doStart();
  }

  function pausePlay() {
    P.playing = false;
    el("playBtn").classList.remove("playing");
    clearTimeout(P.timer);
    P.players.forEach(function (a) { try { a.pause(); } catch (e) { } });
  }

  function stopPlay(finished) {
    pausePlay();
    P.i = 0; P.dirty = true;
    el("plBar").style.width = finished ? "100%" : "0%";
    el("plLabel").textContent = "未播放";
    clearHL();
  }

  function togglePlay() { if (P.playing) pausePlay(); else startPlay(); }

  function jumpUnit(delta) {
    if (!P.units.length || !P.list.length || P.dirty) {
      buildUnits(el("scopeSel").value, function () {
        P.dirty = false; expand(); jumpUnit(delta);
      });
      return;
    }
    var curUid = P.list[P.i] ? P.list[P.i].uid : null, ui = 0;
    for (var k = 0; k < P.units.length; k++) if (P.units[k].id === curUid) { ui = k; break; }
    ui = Math.max(0, Math.min(P.units.length - 1, ui + delta));
    var target = P.units[ui].id, ni = -1;
    for (var j = 0; j < P.list.length; j++) if (P.list[j].uid === target) { ni = j; break; }
    if (ni < 0) return;
    P.i = ni;
    if (P.playing) { clearTimeout(P.timer); step(); }
    else { highlight(target); updateProgress(); }
  }

  function say(src, btn) {
    var a = new Audio(src);
    a.playbackRate = rate();
    if (btn) {
      btn.classList.add("on");
      a.onended = a.onerror = function () { btn.classList.remove("on"); };
    }
    var pr = a.play();
    if (pr && pr.catch) pr.catch(function () { if (btn) btn.classList.remove("on"); });
  }

  /* 点读（事件委托） */
  document.addEventListener("click", function (e) {
    var t = e.target && e.target.closest ? e.target.closest("[data-a]") : null;
    if (!t) return;
    var src = t.getAttribute("data-a");
    if (!src) return;
    if (t.classList.contains("spk")) { e.stopPropagation(); say(src, t); }
    else say(src, null);
  });

  /* ---------- 搜索 ---------- */
  var searchTimer = null;
  function doSearch(q) {
    q = (q || "").trim().toLowerCase();
    var box = el("searchResults");
    if (!q) { box.classList.add("hidden"); content.classList.remove("hidden"); return; }
    loadAll(function () {
      var res = [], seen = {};
      FLAT.forEach(function (f) {
        var d = DATA[f.gid]; if (!d) return;
        d.secs.forEach(function (s) {
          var push = function (es, zh, pos) {
            var k = es + "|" + zh;
            if (seen[k]) return; seen[k] = 1;
            if (es.toLowerCase().indexOf(q) >= 0 || zh.toLowerCase().indexOf(q) >= 0)
              res.push({ es: es, zh: zh, pos: pos, f: f, s: s });
          };
          s.w.forEach(function (x) { push(x[1], x[0], x[2]); });
          s.e.forEach(function (x) { push(x[1], x[0], x[2]); });
        });
      });
      var h = '<div class="sr-head">找到 ' + res.length + ' 条'
        + (res.length > 300 ? "（仅显示前 300 条）" : "") + '</div>';
      res.slice(0, 300).forEach(function (r) {
        var gid = r.f.gid, sno = r.s.no;
        h += '<div class="sr-item" data-gid="' + gid + '" data-sno="' + sno + '">'
          + '<span class="sr-es">' + esc(r.es) + '</span>'
          + '<span class="sr-zh">' + esc(r.zh) + '</span>'
          + '<span class="sr-pos">Parte ' + r.f.no + ' · ' + esc(r.f.name) + '</span></div>';
      });
      if (!res.length) h += '<div class="empty">没有匹配的词条</div>';
      box.innerHTML = h;
      box.classList.remove("hidden");
      content.classList.add("hidden");
      box.querySelectorAll(".sr-item").forEach(function (it) {
        it.onclick = function () {
          gotoSec(parseInt(it.getAttribute("data-gid"), 10),
                  parseInt(it.getAttribute("data-sno"), 10));
        };
      });
    });
  }

  function gotoSec(gid, sno) {
    for (var i = 0; i < FLAT.length; i++) {
      if (FLAT[i].gid !== gid) continue;
      var secs = META.grupos[FLAT[i].g].partes[FLAT[i].p].secs;
      for (var j = 0; j < secs.length; j++) {
        if (secs[j].no === sno) {
          state.g = FLAT[i].g; state.p = FLAT[i].p; state.s = j; savePos();
          el("search").value = "";
          el("searchResults").classList.add("hidden");
          content.classList.remove("hidden");
          render(); return;
        }
      }
    }
  }

  /* ---------- 初始化 ---------- */
  function init() {
    buildFlat();
    loadLS();
    el("bookTitle").textContent = META.title || "意大利语单词随身背";
    el("bookAuthor").textContent = META.author || "";
    renderToc();

    el("toc").addEventListener("click", function (e) {
      if (!e.target.closest) return;
      var gh = e.target.closest(".grupo-hd");
      if (gh) {
        var gi = parseInt(gh.getAttribute("data-g"), 10);
        var item = gh.parentElement;
        item.classList.toggle("open");
        if (item.classList.contains("open") && gi !== state.g) {
          state.g = gi; state.p = 0; state.s = 0; savePos(); render();
        }
        return;
      }
      var ph = e.target.closest(".parte-hd");
      if (ph) {
        var pgi = parseInt(ph.getAttribute("data-g"), 10);
        var ppi = parseInt(ph.getAttribute("data-p"), 10);
        var pitem = ph.parentElement;
        var wasOpen = pitem.classList.contains("open");
        var allP = pitem.parentElement.querySelectorAll(".parte-item");
        for (var k = 0; k < allP.length; k++) allP[k].classList.remove("open");
        if (!wasOpen || !(pgi === state.g && ppi === state.p)) {
          pitem.classList.add("open");
          state.g = pgi; state.p = ppi; state.s = 0; savePos(); render();
        }
        return;
      }
      var si = e.target.closest(".sec-item");
      if (si) {
        state.g = parseInt(si.getAttribute("data-g"), 10);
        state.p = parseInt(si.getAttribute("data-p"), 10);
        state.s = parseInt(si.getAttribute("data-s"), 10);
        savePos(); render(); closeSide();
      }
    });

    el("playBtn").onclick = togglePlay;
    el("prevBtn").onclick = function () { jumpUnit(-1); };
    el("nextBtn").onclick = function () { jumpUnit(1); };
    el("modeSel").onchange = function () { P.dirty = true; expand(); P.i = 0; updateProgress(); };
    el("scopeSel").onchange = function () { P.dirty = true; pausePlay(); P.i = 0; updateProgress(); };
    el("rateSel").onchange = function () {
      P.players.forEach(function (a) { a.playbackRate = rate(); });
    };
    el("plBar").parentElement.onclick = function (e) {
      if (!P.list.length) return;
      var r = this.getBoundingClientRect();
      var pct = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
      P.i = Math.min(P.list.length - 1, Math.floor(pct * P.list.length));
      if (P.playing) { clearTimeout(P.timer); step(); } else updateProgress();
    };

    el("search").addEventListener("input", function () {
      clearTimeout(searchTimer);
      var v = this.value;
      searchTimer = setTimeout(function () { doSearch(v); }, 220);
    });
    el("searchClear").onclick = function () {
      el("search").value = "";
      el("searchResults").classList.add("hidden");
      content.classList.remove("hidden");
    };

    el("themeBtn").onclick = function () {
      state.theme = state.theme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", state.theme);
      localStorage.setItem(LS_THEME, state.theme);
    };
    el("helpBtn").onclick = function () { el("helpModal").classList.remove("hidden"); };
    el("pronBtn").onclick = function () {
      document.body.classList.toggle("hide-pron");
      var on = !document.body.classList.contains("hide-pron");
      localStorage.setItem("sv15000_pron", on ? "1" : "0");
    };
    if (localStorage.getItem("sv15000_pron") === "0")
      document.body.classList.add("hide-pron");
    el("helpClose").onclick = function () { el("helpModal").classList.add("hidden"); };
    el("helpModal").onclick = function (e) { if (e.target === this) this.classList.add("hidden"); };
    el("exportBtn").onclick = exportProgress;
    el("importFile").onchange = function (e) {
      var f = e.target.files && e.target.files[0];
      if (f) importProgress(f);
      e.target.value = "";
    };

    var openSide = function () { el("sidebar").classList.add("show"); el("scrim").classList.remove("hidden"); };
    function closeSide() { el("sidebar").classList.remove("show"); el("scrim").classList.add("hidden"); }
    window.closeSide = closeSide;
    el("menuBtn").onclick = openSide;
    el("menuBtn2").onclick = openSide;
    el("scrim").onclick = closeSide;

    document.addEventListener("keydown", function (e) {
      if (study.active) {
        if (study.mode === "card") {
          var back = el("studyBody").querySelector(".back");
          if (e.key === " ") {
            e.preventDefault();
            if (back) grade(true);
            else if (study.cur) flipCard(study.cur, el("studyBody"), el("studyFoot"));
          } else if (e.key === "ArrowRight") { e.preventDefault(); if (back) grade(true); }
          else if (e.key === "ArrowLeft") { e.preventDefault(); if (back) grade(false); }
        }
        return;
      }
      var tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "select" || tag === "textarea") {
        if (e.key === "Escape") e.target.blur();
        return;
      }
      if (e.key === " ") { e.preventDefault(); togglePlay(); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); jumpUnit(-1); }
      else if (e.key === "ArrowRight") { e.preventDefault(); jumpUnit(1); }
      else if (e.key === "/") { e.preventDefault(); el("search").focus(); }
    });

    setTimeout(function () {
      var fi = flatIndex();
      for (var k = 1; k <= 2; k++) if (FLAT[fi + k]) loadParte(FLAT[fi + k].gid, function () { });
    }, 1200);

    initStudy();
    render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  /* ============ 学习模式：闪卡 / 测验 + SRS 间隔重复 ============ */
  function loadSRS() { try { study.srs = JSON.parse(localStorage.getItem(LS_SRS) || "{}"); } catch (e) { study.srs = {}; } }
  function saveSRS() { try { localStorage.setItem(LS_SRS, JSON.stringify(study.srs)); } catch (e) { } }
  function srsUpdate(u, known) {
    var r = study.srs[u] || { b: 0, due: 0, reps: 0, lap: 0 };
    r.reps = (r.reps || 0) + 1;
    if (known) { r.b = Math.min((r.b || 0) + 1, SRS_INT.length - 1); r.lap = 0; }
    else { r.lap = (r.lap || 0) + 1; r.b = 0; }
    r.due = Date.now() + (SRS_INT[r.b] || 0);
    study.srs[u] = r; saveSRS();
  }
  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function studySections(scope, cb) {
    if (scope === "sec") {
      loadParte(curParte().gid, function (d) {
        if (!d) { cb([]); return; }
        var sec = null;
        for (var i = 0; i < d.secs.length; i++) if (d.secs[i].no === curSec().no) sec = d.secs[i];
        cb(sec ? [{ gid: curParte().gid, sec: sec }] : []);
      });
    } else if (scope === "parte") {
      loadParte(curParte().gid, function (d) {
        cb(d ? d.secs.map(function (s) { return { gid: curParte().gid, sec: s }; }) : []);
      });
    } else {
      loadAll(function () {
        var list = [];
        FLAT.forEach(function (f) {
          var d = DATA[f.gid]; if (!d) return;
          d.secs.forEach(function (s) { list.push({ gid: f.gid, sec: s }); });
        });
        cb(list);
      });
    }
  }
  function buildStudyItems(scope, cb) {
    studySections(scope, function (pairs) {
      var out = [];
      pairs.forEach(function (p) {
        ["w", "e", "s"].forEach(function (kind) {
          p.sec[kind].forEach(function (it, i) {
            out.push({
              uid: uid(p.gid, p.sec.no, kind, i), kind: kind,
              es: it[(kind === "s" ? 0 : 1)], zh: it[(kind === "s" ? 1 : 0)],
              ae: it[3], az: it[4], py: it[5], ipa: it[6]
            });
          });
        });
      });
      cb(out);
    });
  }

  function startStudy() {
    stopPlay();
    study.active = true;
    study.scope = el("studyScope").value;
    study.mode = (document.querySelector(".stab.active") || { getAttribute: function () { return "card"; } })
      .getAttribute("data-smode");
    study.dueOnly = el("studyDue").checked;
    el("study").classList.remove("hidden");
    document.body.classList.add("study-on");
    buildStudyItems(study.scope, function (items) {
      if (study.mode === "quiz") items = items.filter(function (x) { return x.kind !== "s"; });
      if (study.dueOnly) {
        var due = items.filter(function (it) { var r = study.srs[it.uid]; return !r || r.due <= Date.now(); });
        if (due.length) items = due;
      }
      if (el("studyShuffle").checked) shuffle(items);
      study.items = items; study.i = 0; study.total = items.length;
      study.known = 0; study.unknown = 0; study.cur = null;
      if (!items.length) {
        el("studyBody").innerHTML = '<div class="empty">本节暂无可学习词条</div>';
        el("studyFoot").innerHTML = "";
        return;
      }
      renderStudy();
    });
  }

  function renderStudy() {
    if (study.i >= study.items.length) { renderStudyDone(); return; }
    study.cur = study.items[study.i];
    if (study.mode === "card") renderCard(study.cur, el("studyBody"), el("studyFoot"));
    else renderQuiz(study.cur, el("studyBody"), el("studyFoot"));
  }

  function renderCard(it, body, foot) {
    body.innerHTML = '<div class="card-face front">'
      + '<div class="cf-es">' + esc(it.es) + '</div>'
      + (it.ipa ? '<div class="cf-ipa">/' + esc(it.ipa) + '/</div>' : '')
      + '<button class="cf-spk spk" data-a="' + AUDIO + it.ae + '" title="意语发音">🔊 意语</button>'
      + '<div class="cf-hint">点击卡片或按空格翻面</div></div>';
    body.onclick = function (e) { if (e.target.closest(".spk")) return; flipCard(it, body, foot); };
    foot.innerHTML = '<div class="study-prog">' + (study.i + 1) + ' / ' + study.total + '</div>'
      + '<button class="btn primary" id="sFlip">翻面看中文</button>';
    el("sFlip").onclick = function (e) { e.stopPropagation(); flipCard(it, body, foot); };
  }
  function flipCard(it, body, foot) {
    body.onclick = null;
    body.innerHTML = '<div class="card-face back">'
      + '<div class="cf-zh">' + esc(it.zh) + '</div>'
      + (it.py ? '<div class="cf-py">' + esc(it.py) + '</div>' : '')
      + '<button class="cf-spk spk" data-a="' + AUDIO + it.az + '" title="中文发音">🔊 中文</button>'
      + (it.kind === "s" && it.src ? '<div class="cf-src">' + esc(it.src) + '</div>' : '')
      + '</div>';
    foot.innerHTML = '<div class="study-prog">' + (study.i + 1) + ' / ' + study.total + '</div>'
      + '<button class="btn s-unknown" id="sUnknown">不认识</button>'
      + '<button class="btn primary s-known" id="sKnown">认识</button>';
    el("sKnown").onclick = function () { grade(true); renderStudy(); };
    el("sUnknown").onclick = function () { grade(false); renderStudy(); };
  }

  function renderQuiz(it, body, foot) {
    body.onclick = null;
    var pool = study.items.filter(function (x) { return x.uid !== it.uid && x.kind !== "s"; });
    shuffle(pool);
    var seen = {}, opts = [];
    function add(o) { if (!seen[o]) { seen[o] = 1; opts.push(o); } }
    add(it.es);
    for (var k = 0; k < pool.length && opts.length < 4; k++) add(pool[k].es);
    shuffle(opts);
    body.innerHTML = '<div class="quiz-prompt"><div class="qp-zh">' + esc(it.zh) + '</div>'
      + (it.py ? '<div class="qp-py">' + esc(it.py) + '</div>' : '')
      + '<button class="cf-spk spk" data-a="' + AUDIO + it.az + '" title="中文发音">🔊 中文</button></div>'
      + '<div class="quiz-opts">' + opts.map(function (o) {
        return '<button class="qopt" data-es="' + esc(o) + '">' + esc(o) + '</button>';
      }).join("") + '</div>';
    body.querySelectorAll(".qopt").forEach(function (b) {
      b.onclick = function () {
        var chosen = b.getAttribute("data-es"), correct = (chosen === it.es);
        body.querySelectorAll(".qopt").forEach(function (x) {
          x.disabled = true;
          if (x.getAttribute("data-es") === it.es) x.classList.add("correct");
          else if (x === b) x.classList.add("wrong");
        });
        say(AUDIO + it.ae, null);
        grade(correct);
        setTimeout(renderStudy, 1200);
      };
    });
    foot.innerHTML = '<div class="study-prog">' + (study.i + 1) + ' / ' + study.total + '</div>';
  }

  function grade(known) {
    var it = study.items[study.i];
    if (!it) return;
    srsUpdate(it.uid, known);
    if (known) study.known++; else study.unknown++;
    study.i++;
  }

  function renderStudyDone() {
    var body = el("studyBody"), foot = el("studyFoot");
    body.innerHTML = '<div class="study-done"><div class="sd-title">本轮完成 🎉</div>'
      + '<div class="sd-stat">共 ' + study.total + ' 张 · 认识 ' + study.known
      + ' · 待巩固 ' + study.unknown + '</div></div>';
    foot.innerHTML = '<button class="btn primary" id="sAgain">再来一轮</button>'
      + '<button class="btn" id="sClose2">退出</button>';
    el("sAgain").onclick = startStudy;
    el("sClose2").onclick = closeStudy;
  }
  function closeStudy() {
    study.active = false; study.cur = null;
    el("study").classList.add("hidden");
    document.body.classList.remove("study-on");
  }

  function exportProgress() {
    var data = { v: 1, ts: Date.now(),
      done: localStorage.getItem(LS_DONE) || "{}",
      srs: localStorage.getItem(LS_SRS) || "{}" };
    try {
      var blob = new Blob([JSON.stringify(data, null, 1)], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = "italian-vocab-progress.json";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
    } catch (e) { alert("导出失败：" + e.message); }
  }
  function importProgress(file) {
    var r = new FileReader();
    r.onload = function () {
      try {
        var d = JSON.parse(r.result);
        if (d.done) localStorage.setItem(LS_DONE, d.done);
        if (d.srs) localStorage.setItem(LS_SRS, d.srs);
        state.done = JSON.parse(localStorage.getItem(LS_DONE) || "{}");
        study.srs = JSON.parse(localStorage.getItem(LS_SRS) || "{}");
        renderToc(); render();
        alert("进度已导入（" + Object.keys(state.done).length + " 个小节 + 复习记录）");
      } catch (e) { alert("导入失败：文件格式不正确"); }
    };
    r.readAsText(file);
  }

  /* ---------- 初始化：学习模式 ---------- */
  function initStudy() {
    loadSRS();
    el("studyBtn").onclick = startStudy;
    el("studyClose").onclick = closeStudy;
    document.querySelectorAll(".stab").forEach(function (b) {
      b.onclick = function () {
        document.querySelectorAll(".stab").forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        startStudy();
      };
    });
    el("studyScope").onchange = startStudy;
    el("studyShuffle").onchange = startStudy;
    el("studyDue").onchange = startStudy;
  }

  window.__SV = { state: state, P: P, DATA: DATA, META: META, FLAT: FLAT, study: study };
})();
