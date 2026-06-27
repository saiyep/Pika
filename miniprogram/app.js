const { ensureSession } = require('./utils/auth');

App({
  globalData: {
    token: '',
    user: null,
  },
  onLaunch() {
    this.globalData.token = wx.getStorageSync('token') || '';
    this.globalData.user = null;
    wx.showLoading({ title: '正在登录中', mask: true });
    ensureSession().finally(() => {
      wx.hideLoading();
    });
  },
});
