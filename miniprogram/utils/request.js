const { BASE_URL } = require('../config');
const { clearSession, getToken } = require('./auth');

function request({ url, method = 'GET', data = {}, header = {} }) {
  const token = getToken();
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
          return;
        }
        if (body && body.code === 401) {
          clearSession();
        }
        reject(body || res);
      },
      fail: reject,
    });
  });
}

module.exports = { request };