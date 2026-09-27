// app.js — 全局数据、CDN 加载、音频引擎、进度与 SRS 存储
const audio = require('./utils/audio.js');

App({
  globalData: {
    // 改为你的 CDN 基础地址（GitHub Pages 或腾讯云 COS+CDN）
    cdn: 'https://realrentao.github.io/italian-15000-words',
    meta: null,
    secCache: {},
    audio: audio,
    settings: { rate: 1, showPron: true },
    done: {},
    srs: {},
    last: null
  },

  onLaunch() {
    const g = this.globalData;
    g.done = wx.getStorageSync('sv_done') || {};
    g.srs = wx.getStorageSync('sv_srs') || {};
    try { g.settings = Object.assign(g.settings, wx.getStorageSync('sv_settings') || {}); } catch (e) {}
    try { g.last = wx.getStorageSync('sv_last') || null; } catch (e) {}
    try { g.checkin = wx.getStorageSync('sv_checkin') || null; } catch (e) {}
    // 云开发：多端进度同步（未开通/无 AppID 时自动降级本地存储）
    const cloud = require('./utils/cloud.js');
    if (cloud.init()) {
      cloud.getOpenid().then(oid => {
        if (!oid) return;
        cloud.setOpenid(oid);
        cloud.loadProgress().then(p => { if (p) this._mergeCloud(p); });
      });
    }
  },

  // 加载目录（带缓存）
  loadMeta(cb) {
    const g = this.globalData;
    if (g.meta) { cb && cb(g.meta); return; }
    wx.request({
      url: g.cdn + '/cdn-staging/meta.json',
      success: r => { if (r.statusCode === 200 && r.data) { g.meta = r.data; cb && cb(r.data); } else cb && cb(null); },
      fail: () => cb && cb(null)
    });
  },

  // 加载单个分册（带缓存）
  loadSec(gid, cb) {
    const g = this.globalData;
    if (g.secCache[gid]) { cb && cb(g.secCache[gid]); return; }
    wx.request({
      url: g.cdn + '/cdn-staging/sec/' + gid + '.json',
      success: r => { if (r.statusCode === 200 && r.data) { g.secCache[gid] = r.data; cb && cb(r.data); } else cb && cb(null); },
      fail: () => cb && cb(null)
    });
  },

  audioUrl(rel) { return rel ? this.globalData.cdn + '/audio/' + rel : ''; },

  markDone(key, v) {
    const g = this.globalData;
    if (v) g.done[key] = 1; else delete g.done[key];
    wx.setStorageSync('sv_done', g.done);
    this._syncCloud();
  },

  setLast(gid, sno) {
    this.globalData.last = { gid: gid, sno: sno };
    wx.setStorageSync('sv_last', this.globalData.last);
  },

  saveSettings() { wx.setStorageSync('sv_settings', this.globalData.settings); this._syncCloud(); },

  // 进度变化后同步到云（降级安全：无云环境时直接跳过）
  _syncCloud() {
    const cloud = require('./utils/cloud.js');
    if (!cloud.isReady()) return;
    cloud.saveProgress({ done: this.globalData.done, srs: this.globalData.srs, settings: this.globalData.settings });
  },

  // 登录后把云上进度合并回本地（done 取并集，srs 取较新记录，settings 以云覆盖）
  _mergeCloud(p) {
    const g = this.globalData;
    if (p.done) Object.keys(p.done).forEach(k => { g.done[k] = 1; });
    if (p.srs) {
      for (const k in p.srs) {
        const r = p.srs[k], local = g.srs[k];
        if (!local || !local.due || (r.due || 0) > local.due) g.srs[k] = r;
      }
    }
    if (p.settings) g.settings = Object.assign(g.settings, p.settings);
    wx.setStorageSync('sv_done', g.done);
    wx.setStorageSync('sv_srs', g.srs);
    wx.setStorageSync('sv_settings', g.settings);
  },

  // SRS：5 档间隔（毫秒）
  srsUpdate(uid, known) {
    const g = this.globalData;
    const INT = [0, 600000, 3600000, 86400000, 259200000, 604800000];
    let r = g.srs[uid] || { b: 0, due: 0, reps: 0 };
    r.reps = (r.reps || 0) + 1;
    if (known) r.b = Math.min((r.b || 0) + 1, INT.length - 1);
    else r.b = 0;
    r.due = Date.now() + (INT[r.b] || 0);
    g.srs[uid] = r;
    wx.setStorageSync('sv_srs', g.srs);
    this._syncCloud();
  },

  srsDueCount() {
    const g = this.globalData;
    let n = 0;
    for (const k in g.srs) { const r = g.srs[k]; if (!r || r.due <= Date.now()) n++; }
    return n;
  }
});
