// utils/audio.js — 顺序播放引擎（单例），复刻网页版 P 引擎
// list 项: { src, uid, lang:'it'|'zh' }
class AudioQueue {
  constructor() {
    this.pool = [];
    this.list = [];
    this.index = 0;
    this.playing = false;
    this.rate = 1;
    this.gap = 400;
    this.loop = false;
    this.shuffle = false;
    this._busy = false;
    this._updateCbs = [];
    this._stateCbs = [];
  }

  _ctx() {
    if (this.pool.length < 2) {
      const c = wx.createInnerAudioContext();
      this.pool.push(c);
    }
    return this.pool[this.index % this.pool.length];
  }

  setList(list) { this.list = list || []; this.index = 0; }
  setRate(r) { this.rate = r; }
  setGap(g) { this.gap = g; }
  setLoop(v) { this.loop = v; }
  setShuffle(v) {
    this.shuffle = v;
    if (v) this.list = this._shuffle(this.list.slice());
  }

  _shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  on(cb) { this._updateCbs.push(cb); return cb; }
  off(cb) { this._updateCbs = this._updateCbs.filter(x => x !== cb); }
  onState(cb) { this._stateCbs.push(cb); return cb; }
  offState(cb) { this._stateCbs = this._stateCbs.filter(x => x !== cb); }
  _emitUpdate(s) { this._updateCbs.forEach(cb => cb(s)); }
  _emitState(s) { this._stateCbs.forEach(cb => cb(s)); }

  play() {
    if (!this.list.length) return;
    if (this.index >= this.list.length) this.index = 0;
    this.playing = true;
    this._emitState({ playing: true });
    this._step();
  }

  _step() {
    if (!this.playing) return;
    if (this.index >= this.list.length) {
      if (this.loop) {
        if (this.shuffle) this.list = this._shuffle(this.list.slice());
        this.index = 0;
      } else {
        this.playing = false;
        this._emitState({ playing: false });
        return;
      }
    }
    const item = this.list[this.index];
    const c = this._ctx();
    try { c.stop(); } catch (e) {}
    c.src = item.src;
    c.playbackRate = this.rate;
    const self = this;
    c.onEnded = function () { if (self._busy) return; self._busy = true; self._advance(); };
    c.onError = function () { if (self._busy) return; self._busy = true; self._advance(); };
    const pr = c.play();
    if (pr && pr.catch) pr.catch(function () { if (!self._busy) { self._busy = true; self._advance(); } });
    this._emitUpdate({ index: this.index, total: this.list.length, item: item });
  }

  _advance() {
    this._busy = false;
    this.index++;
    this._step();
  }

  pause() {
    this.playing = false;
    this.pool.forEach(c => { try { c.pause(); } catch (e) {} });
    this._emitState({ playing: false });
  }

  stop() {
    this.pause();
    this.index = 0;
    this._emitUpdate({ index: 0, total: this.list.length, item: this.list[0] || null });
  }

  toggle() { if (this.playing) this.pause(); else this.play(); }

  next() { if (this.index < this.list.length - 1) { this.index++; if (this.playing) this._step(); } }
  prev() { if (this.index > 0) { this.index--; if (this.playing) this._step(); } }
  seek(i) {
    this.index = i;
    if (this.playing) this._step();
    else this._emitUpdate({ index: i, total: this.list.length, item: this.list[i] || null });
  }
}

module.exports = new AudioQueue();
