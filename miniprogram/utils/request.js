const { BASE_URL } = require('../config');

function request({ url, method = 'GET', data = {}, header = {} }) {
  const token = getApp().globalData.token || wx.getStorageSync('token') || '';
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + url,
      method,
      data,
      header: { 'X-Pika-Token': token, ...header },
      success(res) {
        const body = res.data;
        if (body && body.code === 0) {
          resolve(body.data);
        } else {
          reject(body || res);
        }
      },
      fail: reject,
    });
  });
}

module.exports = { request };
