const { BASE_URL } = require('../config');
const { clearSession, ensureSession, getToken } = require('./auth');

function request({ url, method = 'GET', data = {}, header = {} }) {
  const doRequest = () => {
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
          reject(body || res);
        },
        fail: reject,
      });
    });
  };

  return doRequest().catch((err) => {
    if (!(err && err.code === 401)) {
      throw err;
    }
    clearSession();
    return ensureSession().then((ok) => {
      if (!ok) throw err;
      return doRequest();
    });
  });
}

module.exports = { request };