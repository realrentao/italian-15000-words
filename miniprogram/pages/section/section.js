const app = getApp();
const audio = app.globalData.audio;

Page({
  data: {
    gid: 0, sno: 0, grupoName: '', parteName: '', secName: '',
    w: [], s: [], e: [], done: false,
    curUid: '', plIndex: 0, plTotal: 0, plLabel: '未播放', rate: 1,
    range: 'block'
  },

  onLoad(q) {
    const gid = +q.gid, sno = +q.sno;
    this.setData({ gid: gid, sno: sno, rate: app.globalData.settings.rate || 1 });
    app.loadSec(gid, d => {
      if (!d) { wx.showToast({ title: '加载失败', icon: 'none' }); return; }
      const meta = app.globalData.meta;
      let gn = '', pn = '', sec = null;
      meta.grupos.forEach(g => g.partes.forEach(p => {
        if (p.gid === gid) { gn = g.name; pn = p.name; sec = p.secs.find(x => x.no === sno); }
      }));
      this._sec = sec;
      this.setData({
        grupoName: gn, parteName: pn, secName: sec ? sec.name : '',
        w: sec ? sec.w : [], s: sec ? sec.s : [], e: sec ? sec.e : [],
        done: !!app.globalData.done[gid + '-' + sno]
      });
    });
    this._u = audio.on(st => this.setData({ plIndex: st.index, plTotal: st.total, curUid: st.item ? st.item.uid : '', plLabel: this._label(st) }));
    this._st = audio.onState(st => this.setData({ playing: st.playing }));
  },

  onUnload() { audio.off(this._u); audio.offState(this._st); audio.stop(); },

  _label(st) {
    if (!st.total) return '未播放';
    const lang = st.item && st.item.lang === 'zh' ? '中文' : '意语';
    return '第 ' + (st.index + 1) + '/' + st.total + ' 条 · ' + lang;
  },

  // 点读：单条播放
  say(e) {
    const rel = e.currentTarget.dataset.a;
    if (!rel) return;
    const c = wx.createInnerAudioContext();
    c.src = app.audioUrl(rel);
    c.playbackRate = this.data.rate;
    c.play();
  },

  // 阴阳连读（阳性 → 阴性）
  saySeq(e) {
    const a1 = e.currentTarget.dataset.a, a2 = e.currentTarget.dataset.a2;
    if (!a1) return;
    const c = wx.createInnerAudioContext();
    c.src = app.audioUrl(a1);
    c.playbackRate = this.data.rate;
    if (a2) c.onEnded = () => { c.src = app.audioUrl(a2); c.play(); };
    c.play();
  },

  // 连播本小节某一类（意→中逐条）
  playBlock(e) {
    const kind = e.currentTarget.dataset.kind;
    const sec = this._sec;
    if (!sec) return;
    const units = this._unitsOf(sec).filter(u => u.kind === kind);
    const list = this._expand('it-zh', units);
    audio.setRate(this.data.rate);
    audio.setList(list);
    audio.play();
  },

  _unitsOf(sec) {
    const gid = this.data.gid, sno = this.data.sno, out = [];
    (sec.w || []).forEach((it, i) => out.push({ uid: 'u' + gid + '_' + sno + '_w_' + i, kind: 'w', ae: it[3], az: it[4], af: it[7] || '' }));
    (sec.s || []).forEach((it, i) => out.push({ uid: 'u' + gid + '_' + sno + '_s_' + i, kind: 's', ae: it[3], az: it[4], af: '' }));
    (sec.e || []).forEach((it, i) => out.push({ uid: 'u' + gid + '_' + sno + '_e_' + i, kind: 'e', ae: it[3], az: it[4], af: it[7] || '' }));
    return out;
  },

  _expand(mode, units) {
    const A = app, L = [];
    const pushIt = u => { L.push({ src: A.audioUrl(u.ae), uid: u.uid, lang: 'it' }); if (u.af) L.push({ src: A.audioUrl(u.af), uid: u.uid, lang: 'it' }); };
    units.forEach(u => {
      if (mode === 'it-zh') { pushIt(u); L.push({ src: A.audioUrl(u.az), uid: u.uid, lang: 'zh' }); }
      else if (mode === 'it-only') { pushIt(u); }
      else if (mode === 'zh-only') { L.push({ src: A.audioUrl(u.az), uid: u.uid, lang: 'zh' }); }
      else { pushIt(u); }
    });
    if (mode === 'all-it-zh') units.forEach(u => L.push({ src: A.audioUrl(u.az), uid: u.uid, lang: 'zh' }));
    return L;
  },

  // 范围连播：本小节 / 本篇 / 全书
  setRange(e) { this.setData({ range: e.currentTarget.dataset.r }); },

  playRange() {
    const g = app.globalData, meta = g.meta;
    const gid = this.data.gid, sno = this.data.sno;
    let targets = [];
    if (this.data.range === 'block') {
      targets = [{ gid: gid, sno: sno }];
    } else if (this.data.range === 'parte') {
      meta.grupos.forEach(gr => gr.partes.forEach(p => {
        if (p.gid === gid) p.secs.forEach(s => targets.push({ gid: gid, sno: s.no }));
      }));
    } else {
      meta.grupos.forEach(gr => gr.partes.forEach(p => p.secs.forEach(s => targets.push({ gid: p.gid, sno: s.no }))));
    }
    const self = this;
    wx.showLoading({ title: '准备连播…', mask: true });
    this._collectUnits(targets, units => {
      wx.hideLoading();
      if (!units.length) { wx.showToast({ title: '无内容', icon: 'none' }); return; }
      if (self.data.range === 'book' && units.length > 800) {
        wx.showModal({
          title: '全书连播',
          content: '全书约 ' + units.length + ' 条（意+中各一遍），预计较长，是否开始？',
          success(r) { if (r.confirm) self._startRange(units); }
        });
      } else {
        self._startRange(units);
      }
    });
  },

  // 串行加载目标小节并收集播放单元（带节流，避免瞬时海量请求）
  _collectUnits(targets, cb) {
    const self = this, units = [];
    let i = 0;
    const step = () => {
      if (i >= targets.length) { cb(units); return; }
      const t = targets[i++];
      app.loadSec(t.gid, d => {
        if (d) {
          const sec = (d.secs || []).find(s => s.no === t.sno);
          if (sec) self._unitsOf(sec).forEach(u => units.push(u));
        }
        if (i % 8 === 0) setTimeout(step, 30); else step();
      });
    };
    step();
  },

  _startRange(units) {
    const list = this._expand('it-zh', units);
    audio.setRate(this.data.rate);
    audio.setList(list);
    audio.play();
    wx.showToast({ title: '连播 ' + units.length + ' 条', icon: 'none' });
  },

  markDone() {
    const key = this.data.gid + '-' + this.data.sno;
    const v = !this.data.done;
    app.markDone(key, v);
    this.setData({ done: v });
  },

  startStudy() {
    wx.navigateTo({ url: '/pages/study/study?gid=' + this.data.gid + '&sno=' + this.data.sno });
  },

  onShareAppMessage() {
    const t = this.data.secName ? ('「' + this.data.secName + '」') : '意大利语单词';
    return { title: '跟我背' + t + ' · 意语15000词随身背', path: '/pages/section/section?gid=' + this.data.gid + '&sno=' + this.data.sno };
  },
  onShareTimeline() {
    return { title: '意语15000词随身背 · ' + (this.data.secName || '单词学习') };
  }
});
