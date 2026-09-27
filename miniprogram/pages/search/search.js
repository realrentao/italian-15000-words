const app = getApp();

function fold(s) {
  return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

Page({
  data: { q: '', results: [], loading: false },
  _gids: null,
  _t: null,

  input(e) {
    const v = e.detail.value;
    this.setData({ q: v });
    if (!v) { this.setData({ results: [] }); return; }
    clearTimeout(this._t);
    const self = this;
    this._t = setTimeout(() => self._search(v), 250);
  },

  clear() { this.setData({ q: '', results: [] }); },

  _allGids() {
    if (this._gids) return this._gids;
    const m = app.globalData.meta;
    const ids = [];
    m.grupos.forEach(g => g.partes.forEach(p => ids.push(p.gid)));
    this._gids = ids;
    return ids;
  },

  _search(q) {
    const self = this;
    const fq = fold(q);
    const gids = this._allGids();
    let left = gids.length;
    if (!left) { this.setData({ loading: false, results: [] }); return; }
    this.setData({ loading: true });
    const res = [];
    const seen = {};
    const gnameOf = {}, pnameOf = {};
    app.globalData.meta.grupos.forEach(g => g.partes.forEach(p => { gnameOf[p.gid] = g.name; pnameOf[p.gid] = p.name; }));
    gids.forEach(gid => {
      app.loadSec(gid, d => {
        if (d) {
          d.secs.forEach(s => {
            const push = (es, zh) => {
              const k = 't|' + es + '|' + zh;
              if (seen[k]) return; seen[k] = 1;
              if (fold(es).indexOf(fq) >= 0 || fold(zh).indexOf(fq) >= 0)
                res.push({ uid: gid + '-' + s.no + '-' + es, es, zh, gid, sno: s.no, gname: gnameOf[gid], pname: pnameOf[gid] });
            };
            (s.w || []).forEach(x => push(x[1], x[0]));
            (s.e || []).forEach(x => push(x[1], x[0]));
            (s.s || []).forEach(x => push(x[0], x[1]));
          });
        }
        if (--left <= 0) self.setData({ loading: false, results: res.slice(0, 300) });
      });
    });
  },

  open(e) {
    const gid = +e.currentTarget.dataset.gid, sno = +e.currentTarget.dataset.sno;
    app.setLast(gid, sno);
    wx.navigateTo({ url: '/pages/section/section?gid=' + gid + '&sno=' + sno });
  }
});
