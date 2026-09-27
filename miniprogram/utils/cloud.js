// utils/cloud.js — 微信云开发进度同步（无云环境时自动降级本地存储）
// 使用步骤：
//   1. 微信公众平台开通「云开发」，新建环境，复制环境 ID 填入下方 ENV。
//   2. 在云开发控制台创建集合 progress（权限：仅创建者可读写）。
//   3. 部署 cloudfunctions/getOpenid 云函数（获取 OPENID）。
//   4. project.config.json 的 appid 改为你自己的小程序 AppID。
const ENV = 'your-cloud-env-id'; // ← 替换为你的云开发环境 ID

let ready = false;
let openid = '';

function init() {
  if (wx.cloud) {
    try {
      wx.cloud.init({ env: ENV, traceUser: true });
      ready = true;
    } catch (e) {
      ready = false;
    }
  }
  return ready;
}

function getOpenid() {
  return new Promise((resolve) => {
    if (!ready) return resolve('');
    wx.cloud.callFunction({ name: 'getOpenid' })
      .then(r => resolve((r.result && r.result.openid) || ''))
      .catch(() => resolve(''));
  });
}

function db() { return ready ? wx.cloud.database() : null; }

// 全量覆盖式保存（done/srs/settings 聚合为一份文档，以 openid 为 docId）
function saveProgress(obj) {
  if (!ready || !openid) return Promise.resolve(false);
  const d = db();
  if (!d) return Promise.resolve(false);
  return d.collection('progress').doc(openid).set({
    data: Object.assign({ _openid: openid, updatedAt: Date.now() }, obj)
  }).then(() => true).catch(() => false);
}

function loadProgress() {
  if (!ready || !openid) return Promise.resolve(null);
  const d = db();
  if (!d) return Promise.resolve(null);
  return d.collection('progress').doc(openid).get()
    .then(r => r.data || null)
    .catch(() => null);
}

module.exports = {
  ENV,
  init, getOpenid, saveProgress, loadProgress,
  isReady: () => ready,
  setOpenid: v => { openid = v; }
};
