Page({
  data: {
    userNickname: '',
  },
  onShow() {
    const user = getApp().globalData.user;
    if (user) {
      this.setData({ userNickname: user.nickname || '' });
    }
  },
  goUpload() {
    wx.navigateTo({ url: '/pages/medical/upload/upload' });
  },
  goHistory() {
    wx.navigateTo({ url: '/pages/medical/history/history' });
  },
  goTrend() {
    wx.navigateTo({ url: '/pages/medical/metric-trend/metric-trend' });
  },
  goMembers() {
    wx.navigateTo({ url: '/pages/medical/members/members' });
  },
});
