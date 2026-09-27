// cloudfunctions/getOpenid/index.js
// 返回调用者的 OPENID，用于在小程序端以 openid 为 docId 读写云数据库进度。
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext();
  return { openid: wxContext.OPENID };
};
