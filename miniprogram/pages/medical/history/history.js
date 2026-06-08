const { request } = require('../../../utils/request');

Page({
  data: {
    items: [],
  },
  onShow() {
    this.load();
  },
  load() {
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
  onDelete(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除记录',
      content: '确定删除这条检查记录？原图和数据将一并删除，不可恢复。',
      confirmColor: '#e64340',
      success: (res) => {
        if (!res.confirm) return;
        request({ url: `/api/medical/reports/${id}`, method: 'DELETE' })
          .then(() => {
            this.setData({ items: this.data.items.filter((it) => it.id !== id) });
            wx.showToast({ title: '已删除', icon: 'success' });
          })
          .catch(() => {
            wx.showToast({ title: '删除失败', icon: 'none' });
          });
      },
    });
  },
});
