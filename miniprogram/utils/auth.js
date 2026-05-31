const { BASE_URL } = require('../config');

function login(nickname) {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (!res.code) {
          reject(new Error('wx.login no code'));
          return;
        }
        wx.request({
          url: BASE_URL + '/api/auth/login',
          method: 'POST',
          data: { code: res.code, nickname },
          success(r) {
            const body = r.data;
            if (body && body.code === 0) {
              wx.setStorageSync('token', body.data.token);
              resolve(body.data);
            } else {
              reject(body || r);
            }
          },
          fail: reject,
        });
      },
      fail: reject,
    });
  });
}

module.exports = { login };
