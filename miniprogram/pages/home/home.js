const app = getApp();

Page({
  data: {
    title: '', grupos: [], openG: -1, openP: '',
    doneMap: {}, last: null, doneCount: 0, secTotal: 0, parteCount: 0
  },

  onLoad() {
    this._buildDoneMap();
    app.loadMeta(meta => {
      if (!meta) { wx.showToast({ title: '加载目录失败', icon: 'none' }); return; }
      let pc = 0, sc = 0;
      meta.grupos.forEach(g => { pc += g.partes.length; g.partes.forEach(p => sc += p.secs.length); });
      const last = app.globalData.last;
      let lastInfo = null;
      if (last) {
        meta.grupos.forEach(g => g.partes.forEach(p => {
          if (p.gid === last.gid) {
            const s = p.secs.find(x => x.no === last.sno);
            if (s) lastInfo = { gname: g.name, pname: p.name, sname: s.name };
          }
        }));
      }
      this.setData({
        title: meta.title, grupos: meta.grupos, parteCount: pc, secTotal: sc,
        doneCount: Object.keys(app.globalData.done).length, last: lastInfo
      });
    });
  },

  _buildDoneMap() {
    const m = {};
    const done = app.globalData.done || {};
    for (const k in done) m[k] = 1;
    this.setData({ doneMap: m });
  },

  toggleG(e) {
    const i = +e.currentTarget.dataset.i;
    this.setData({ openG: this.data.openG === i ? -1 : i, openP: '' });
  },

  toggleP(e) {
    const k = e.currentTarget.dataset.k;
    this.setData({ openP: this.data.openP === k ? '' : k });
  },

  openSec(e) {
    const gid = +e.currentTarget.dataset.gid, sno = +e.currentTarget.dataset.sno;
    app.setLast(gid, sno);
    wx.navigateTo({ url: '/pages/section/section?gid=' + gid + '&sno=' + sno });
  },

  continueStudy() {
    const last = app.globalData.last;
    if (last) wx.navigateTo({ url: '/pages/section/section?gid=' + last.gid + '&sno=' + last.sno });
    else wx.switchTab({ url: '/pages/study/study' });
  },

  onShareAppMessage() {
    return { title: '意语15000词随身背 · 真实意大利人配音，9大生活场景随时学', path: '/pages/home/home' };
  },
  onShareTimeline() {
    return { title: '意语15000词随身背 · 边听边背，每天10分钟' };
  }
});
