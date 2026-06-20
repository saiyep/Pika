App({
  globalData: {
    token: '',
    user: null,
  },
  onLaunch() {
    this.globalData.token = wx.getStorageSync('token') || '';
    this.globalData.user = null;
  },
});
