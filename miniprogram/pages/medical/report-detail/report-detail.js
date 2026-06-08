const { request } = require('../../../utils/request');
const { BASE_URL } = require('../../../config');

Page({
  data: {
    report: {},
    metrics: [],
    imageUrl: '',
    reportId: '',
    reparsing: false,
  },
  onLoad(query) {
    const id = query.id;
    this.setData({ reportId: id, imageUrl: BASE_URL + '/api/medical/reports/' + id + '/image' });
    request({ url: '/api/medical/reports/' + id })
      .then((data) => {
        this.setData({ report: data.report, metrics: data.metrics });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },
  previewImage() {
    if (this.data.imageUrl) {
      wx.previewImage({ urls: [this.data.imageUrl] });
    }
  },
  onReparse() {
    if (this.data.reparsing) return;
    this.setData({ reparsing: true });
    request({ url: `/api/medical/reports/${this.data.reportId}/reparse`, method: 'POST' })
      .then((data) => {
        this.setData({ report: data.report, metrics: data.metrics });
        const ok = data.report.status === 'parsed';
        wx.showToast({ title: ok ? '解析成功' : '仍未识别到数据', icon: ok ? 'success' : 'none' });
      })
      .catch((err) => {
        wx.showToast({ title: (err && err.message) || '重新解析失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ reparsing: false });
      });
  },
});
