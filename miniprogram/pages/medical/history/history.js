const { request } = require('../../../utils/request');

Page({
  data: {
    items: [],
  },
  onShow() {
    request({ url: '/api/medical/reports?page=1&size=50' })
      .then((data) => {
        this.setData({ items: data.items });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },
  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/pages/medical/report-detail/report-detail?id=' + id });
  },
});
