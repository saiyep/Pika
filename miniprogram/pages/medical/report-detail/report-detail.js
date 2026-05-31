const { request } = require('../../../utils/request');
const { BASE_URL } = require('../../../config');

Page({
  data: {
    report: {},
    metrics: [],
    imageUrl: '',
  },
  onLoad(query) {
    const id = query.id;
    this.setData({ imageUrl: BASE_URL + '/api/medical/reports/' + id + '/image' });
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
});
