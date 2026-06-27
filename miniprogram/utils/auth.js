const { BASE_URL } = require('../config');

let ensuringSessionPromise = null;

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
    const wait = (ms, fn) => setTimeout(fn, ms);

    const doAttempt = (retryLeft) => {
      wx.login({
        success(res) {
          if (!res.code) {
            if (retryLeft > 0) {
              const attemptNo = 3 - retryLeft;
              wait(200 * attemptNo, () => doAttempt(retryLeft - 1));
              return;
            }
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
                return;
              }
              const rawMsg = String((body && (body.msg || body.errMsg)) || '');
              const canRetryCode = rawMsg.includes('invalid') || rawMsg.includes('code');
              if (retryLeft > 0 && canRetryCode) {
                const attemptNo = 3 - retryLeft;
                wait(250 * attemptNo, () => doAttempt(retryLeft - 1));
                return;
              }
              reject(body || r);
            },
            fail(err) {
              const errMsg = (err && err.errMsg) || '';
              const isNetworkErr = errMsg.includes('ERR_CONNECTION_RESET')
                || errMsg.includes('request:fail')
                || errMsg.includes('timeout')
                || errMsg.includes('connect')
                || errMsg.includes('network');
              if (retryLeft > 0 && isNetworkErr) {
                const attemptNo = 3 - retryLeft;
                wait(300 * attemptNo, () => doAttempt(retryLeft - 1));
                return;
              }
              reject({ errMsg, url: BASE_URL + '/api/auth/login' });
            },
          });
        },
        fail(err) {
          if (retryLeft > 0) {
            const attemptNo = 3 - retryLeft;
            wait(200 * attemptNo, () => doAttempt(retryLeft - 1));
            return;
          }
          reject(err);
        },
      });
    };

    doAttempt(2);
  });
}

function ensureSession(nickname) {
  if (ensuringSessionPromise) return ensuringSessionPromise;
  ensuringSessionPromise = login(nickname)
    .then(() => true)
    .catch(() => {
      clearSession();
      return false;
    })
    .finally(() => {
      ensuringSessionPromise = null;
    });
  return ensuringSessionPromise;
}

function ensureLoginWithModal() {
  return new Promise((resolve) => {
    ensureSession()
      .then((ok) => {
        if (ok) {
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
      })
      .catch(() => {
        resolve(false);
      });
  });
}

module.exports = { login, ensureSession, clearSession, getToken, isLoggedIn, ensureLoginWithModal };