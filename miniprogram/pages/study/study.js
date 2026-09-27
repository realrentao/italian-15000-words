const app = getApp();

Page({
  data: {
    gid: 0, sno: 0, mode: 'card', review: false, quizRev: false,
    items: [], i: 0, total: 0, cur: null, known: 0, unknown: 0, finished: false,
    flipped: false, quizOpts: [], quizChosen: null, quizShow: '', quizAns: '',
    spellVal: '', spellFb: '', spellOk: false
  },

  onLoad(q) {
    this.setData({ gid: +q.gid, sno: +q.sno, review: q.review === '1' });
    if (this.data.review) this._buildReview(); else this._build();
  },

  // 统一构造一条练习项
  _mkItem(gid, sno, kind, idx, it, uid) {
    return {
      uid: uid || ('u' + gid + '_' + sno + '_' + kind + '_' + idx), kind: kind,
      es: kind === 's' ? it[0] : it[1],
      zh: kind === 's' ? it[1] : it[0],
      ae: it[3], az: it[4], py: it[5], ipa: it[6],
      af: kind === 's' ? '' : (it[7] || ''),
      fem: kind === 's' ? '' : (it[8] || '')
    };
  },

  // 常规：当前小节全部词条
  _build() {
    const gid = this.data.gid, sno = this.data.sno;
    app.loadSec(gid, d => {
      if (!d) { wx.showToast({ title: '无内容', icon: 'none' }); return; }
      let sec = null;
      d.secs.forEach(s => { if (s.no === sno) sec = s; });
      if (!sec) { wx.showToast({ title: '无内容', icon: 'none' }); return; }
      const items = [];
      ['w', 'e', 's'].forEach(kind => {
        (sec[kind] || []).forEach((it, idx) => items.push(this._mkItem(gid, sno, kind, idx, it)));
      });
      this._setItems(items);
    });
  },

  // 复习模式：只练 SRS 队列中已到期的词条（跨小节）
  _buildReview() {
    const srs = app.globalData.srs, now = Date.now(), due = [];
    for (const uid in srs) { const r = srs[uid]; if (r && r.due <= now) due.push(uid); }
    if (!due.length) { wx.showToast({ title: '暂无到期复习', icon: 'none' }); this.setData({ finished: true, items: [], total: 0 }); return; }
    // 解析 uid -> 去重到各小节
    const secMap = {};
    due.forEach(uid => {
      const m = /^u(\d+)_(\d+)_(\w+)_(\d+)$/.exec(uid);
      if (!m) return;
      const gid = +m[1], sno = +m[2], kind = m[3], idx = +m[4], key = gid + '-' + sno;
      if (!secMap[key]) secMap[key] = { gid: gid, sno: sno, units: [] };
      secMap[key].units.push({ kind: kind, idx: idx, uid: uid });
    });
    const keys = Object.keys(secMap);
    const items = [];
    if (!keys.length) { this.setData({ finished: true, items: [], total: 0 }); return; }
    wx.showLoading({ title: '加载复习队列', mask: true });
    let done = 0;
    const finish = () => {
      if (++done < keys.length) return;
      wx.hideLoading();
      this._setItems(items);
    };
    keys.forEach(key => {
      const sm = secMap[key];
      app.loadSec(sm.gid, d => {
        if (d) {
          const sec = (d.secs || []).find(s => s.no === sm.sno);
          if (sec) sm.units.forEach(u => {
            const it = (sec[u.kind] || [])[u.idx];
            if (it) items.push(this._mkItem(sm.gid, sm.sno, u.kind, u.idx, it, u.uid));
          });
        }
        finish();
      });
    });
  },

  _setItems(items) {
    this.setData({ items: items, total: items.length, i: 0, known: 0, unknown: 0, finished: items.length === 0 });
    this._render();
  },

  setMode(e) {
    this.setData({ mode: e.currentTarget.dataset.m, i: 0, known: 0, unknown: 0, finished: false, flipped: false, quizChosen: null, quizRev: false, spellVal: '', spellFb: '', spellOk: false });
    this._render();
  },

  // 测验正向/反向切换
  toggleQuizRev() {
    this.setData({ quizRev: !this.data.quizRev, quizChosen: null });
    this._render();
  },

  _shuffle(a) {
    a = a.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  },

  _render() {
    if (this.data.i >= this.data.total) { this.setData({ cur: null, finished: true }); return; }
    const it = this.data.items[this.data.i];
    if (this.data.mode === 'card') {
      this.setData({ cur: it, flipped: false });
    } else if (this.data.mode === 'quiz') {
      // 正向：看中文选意语词；反向：看意语词选中文意思
      const showField = this.data.quizRev ? 'es' : 'zh';
      const ansField = this.data.quizRev ? 'zh' : 'es';
      const pool = this.data.items.filter(x => x.uid !== it.uid && x.kind !== 's');
      const opts = [it[ansField]];
      const seen = {};
      for (const x of this._shuffle(pool)) {
        if (opts.length >= 4) break;
        if (!seen[x[ansField]]) { seen[x[ansField]] = 1; opts.push(x[ansField]); }
      }
      this.setData({ cur: it, quizShow: it[showField], quizOpts: this._shuffle(opts), quizChosen: null, quizAns: it[ansField] });
    } else {
      this.setData({ cur: it, spellVal: '', spellFb: '', spellOk: false });
    }
  },

  flip() {
    if (this.data.mode !== 'card' || !this.data.cur) return;
    if (this.data.flipped) return;
    this.setData({ flipped: true });
    this._speak(app.audioUrl(this.data.cur.az));
  },
  speakIt(e) { e && e.stopPropagation && e.stopPropagation(); this._speak(app.audioUrl(this.data.cur.ae)); },
  speakZh(e) { e && e.stopPropagation && e.stopPropagation(); this._speak(app.audioUrl(this.data.cur.az)); },
  _speak(src) {
    if (!src) return;
    const c = wx.createInnerAudioContext();
    c.src = src; c.playbackRate = app.globalData.settings.rate || 1; c.play();
  },

  choose(e) {
    if (this.data.quizChosen) return;
    const chosen = e.currentTarget.dataset.es;
    const correct = chosen === this.data.quizAns;
    this.setData({ quizChosen: chosen });
    this._grade(correct);
    setTimeout(() => this._next(), 1200);
  },

  onSpell(e) { this.setData({ spellVal: e.detail.value }); },
  check() {
    if (!this.data.cur) return;
    const val = (this.data.spellVal || '').trim().toLowerCase();
    const ans = (this.data.cur.es || '').trim().toLowerCase();
    if (!val) { this.setData({ spellFb: '请输入单词', spellOk: false }); return; }
    const ok = val === ans;
    this.setData({ spellOk: ok, spellFb: ok ? ('✓ 正确 · ' + this.data.cur.es) : ('✗ 正确应为 ' + this.data.cur.es) });
  },

  nextWord() { this._next(); },

  grade(e) {
    const known = +e.currentTarget.dataset.k === 1;
    this._grade(known);
    this._next();
  },

  _grade(known) {
    const it = this.data.cur;
    if (!it) return;
    app.srsUpdate(it.uid, known);
    if (known) this.setData({ known: this.data.known + 1 });
    else this.setData({ unknown: this.data.unknown + 1 });
  },

  _next() { this.setData({ i: this.data.i + 1, flipped: false, quizChosen: null, spellVal: '', spellFb: '', spellOk: false }); this._render(); },
  restart() { this.setData({ i: 0, known: 0, unknown: 0, finished: false }); this._render(); },

  onShareAppMessage() {
    const q = 'gid=' + this.data.gid + '&sno=' + this.data.sno + (this.data.review ? '&review=1' : '');
    return { title: '挑战意语单词 · 闪卡/测验/拼写三模练习', path: '/pages/study/study?' + q };
  },
  onShareTimeline() {
    return { title: '意语15000词随身背 · 闪卡测验拼写练起来' };
  }
});
