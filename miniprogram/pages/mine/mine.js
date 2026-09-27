const app = getApp();

Page({
  data: {
    doneCount: 0, secTotal: 0, dueCount: 0, srsCount: 0,
    showPron: true, rateIdx: 2, rates: ['0.7', '0.85', '1.0', '1.15']
  },

  onShow() {
    const g = app.globalData;
    let sc = 0;
    if (g.meta) g.meta.grupos.forEach(gr => gr.partes.forEach(p => sc += p.secs.length));
    const ck = app.checkinState();
    this.setData({
      doneCount: Object.keys(g.done).length,
      secTotal: sc,
      dueCount: app.srsDueCount(),
      srsCount: Object.keys(g.srs).length,
      showPron: g.settings.showPron !== false,
      rateIdx: this._rateIdx(g.settings.rate || 1),
      ckToday: ck.done, ckStreak: ck.streak, ckWeek: ck.week
    });
  },

  _rateIdx(r) {
    const i = this.data.rates.indexOf(String(r));
    return i < 0 ? 2 : i;
  },

  togglePron(e) {
    app.globalData.settings.showPron = e.detail.value;
    app.saveSettings();
    this.setData({ showPron: e.detail.value });
  },

  onRate(e) {
    const idx = +e.detail.value;
    const r = +this.data.rates[idx];
    app.globalData.settings.rate = r;
    app.saveSettings();
    this.setData({ rateIdx: idx });
  },

  startReview() {
    if (!this.data.dueCount) { wx.showToast({ title: '暂无到期复习', icon: 'none' }); return; }
    wx.navigateTo({ url: '/pages/study/study?review=1' });
  },

  clearProgress() {
    const self = this;
    wx.showModal({
      title: '清空进度',
      content: '将删除全部「已学完」标记与复习记录，确定？',
      success(r) {
        if (r.confirm) {
          app.globalData.done = {};
          app.globalData.srs = {};
          wx.setStorageSync('sv_done', {});
          wx.setStorageSync('sv_srs', {});
          self.onShow();
        }
      }
    });
  }
});
