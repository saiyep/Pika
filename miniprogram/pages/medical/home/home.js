Page({
  data: {},
  goUpload() {
    wx.navigateTo({ url: '/pages/medical/upload/upload' });
  },
  goHistory() {
    wx.navigateTo({ url: '/pages/medical/history/history' });
  },
  goTrend() {
    wx.navigateTo({ url: '/pages/medical/metric-trend/metric-trend' });
  },
  goPermissions() {
    wx.navigateTo({ url: '/pages/medical/permissions/permissions' });
  },
});
