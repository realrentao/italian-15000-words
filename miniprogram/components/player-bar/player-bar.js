const app = getApp();
const audio = app.globalData.audio;

Component({
  data: {
    playing: false, index: 0, total: 0, label: '未播放',
    rateIdx: 2, rates: ['0.7', '0.85', '1.0', '1.15'], loop: false, shuffle: false
  },

  lifetimes: {
    attached() {
      const self = this;
      this._u = audio.on(st => self.setData({ index: st.index, total: st.total, label: self._label(st) }));
      this._st = audio.onState(st => self.setData({ playing: st.playing }));
      this.setData({ rateIdx: self._rateIdx(app.globalData.settings.rate || 1) });
    },
    detached() {
      audio.off(this._u); audio.offState(this._st);
    }
  },

  methods: {
    _label(st) {
      if (!st.total) return '未播放';
      const lang = st.item && st.item.lang === 'zh' ? '中文' : '意语';
      return '第 ' + (st.index + 1) + '/' + st.total + ' 条 · ' + lang;
    },
    _rateIdx(r) {
      const i = this.data.rates.indexOf(String(r));
      return i < 0 ? 2 : i;
    },
    toggle() { audio.toggle(); },
    prev() { audio.prev(); },
    next() { audio.next(); },
    onBarTap(e) {
      const self = this;
      wx.createSelectorQuery().in(this).select('.bar').boundingClientRect(rect => {
        if (!rect || !self.data.total) return;
        const pct = Math.max(0, Math.min(1, (e.detail.x - rect.left) / rect.width));
        audio.seek(Math.min(self.data.total - 1, Math.floor(pct * self.data.total)));
      }).exec();
    },
    onRate(e) {
      const idx = +e.detail.value;
      const r = +this.data.rates[idx];
      audio.setRate(r);
      app.globalData.settings.rate = r; app.saveSettings();
      this.setData({ rateIdx: idx });
    },
    toggleLoop() { const v = !this.data.loop; audio.setLoop(v); this.setData({ loop: v }); },
    toggleShuffle() { const v = !this.data.shuffle; audio.setShuffle(v); this.setData({ shuffle: v }); }
  }
});
