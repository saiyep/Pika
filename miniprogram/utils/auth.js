const { BASE_URL } = require('../config');

function applyLoginResult(data) {
  const app = getApp();
  app.globalData.token = data.token;
  app.globalData.user = data.user;
  wx.setStorageSync('token', data.token);
}

function clearSession() {
  const app = getApp();
  app.globalData.token = '';
  app.globalData.user = null;
  wx.removeStorageSync('token');
}

function getToken() {
  return getApp().globalData.token || wx.getStorageSync('token') || '';
}

function isLoggedIn() {
  return !!getToken();
}

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
              applyLoginResult(body.data);
              resolve(body.data);
            } else {
              reject(body || r);
            }
          },
          fail(err) {
            reject({ errMsg: err && err.errMsg, url: BASE_URL + '/api/auth/login' });
          },
        });
      },
      fail: reject,
    });
  });
}

function ensureLoginWithModal() {
  return new Promise((resolve) => {
    if (isLoggedIn()) {
      resolve(true);
      return;
    }
    wx.showModal({
      title: '请先登录',
      content: '请前往“我”页面完成微信登录',
      confirmText: '去登录',
      cancelText: '取消',
      success: (modalRes) => {
        if (modalRes.confirm) {
          wx.switchTab({ url: '/pages/mine/mine' });
        }
        resolve(false);
      },
      fail: () => resolve(false),
    });
  });
}

module.exports = { login, clearSession, getToken, isLoggedIn, ensureLoginWithModal };