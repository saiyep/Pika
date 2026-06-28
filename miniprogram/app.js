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
    const retryDelays = [0, 1200, 2400];
    const attempt = async (index) => {
      if (index > 0) {
        await new Promise((resolve) => setTimeout(resolve, retryDelays[index]));
      }
      const ok = await ensureSession();
      if (ok || index === retryDelays.length - 1) return ok;
      return attempt(index + 1);
    };
    attempt(0).finally(() => {
      wx.hideLoading();
    });
  },
});
