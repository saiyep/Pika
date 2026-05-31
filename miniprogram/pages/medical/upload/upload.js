const { BASE_URL } = require('../../../config');

Page({
  data: {
    previewPath: '',
    uploading: false,
    result: null,
  },
  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera', 'album'],
      success: (res) => {
        this.setData({ previewPath: res.tempFiles[0].tempFilePath, result: null });
      },
    });
  },
  upload() {
    if (!this.data.previewPath) return;
    const token = getApp().globalData.token || wx.getStorageSync('token') || '';
    this.setData({ uploading: true });
    wx.uploadFile({
      url: BASE_URL + '/api/medical/reports',
      filePath: this.data.previewPath,
      name: 'file',
      header: { 'X-Pika-Token': token },
      success: (res) => {
        try {
          const body = JSON.parse(res.data);
          if (body.code === 0) {
            this.setData({ result: body.data });
          } else {
            wx.showToast({ title: body.msg || '上传失败', icon: 'none' });
          }
        } catch (e) {
          wx.showToast({ title: '返回解析失败', icon: 'none' });
        }
      },
      fail: () => {
        wx.showToast({ title: '网络错误', icon: 'none' });
      },
      complete: () => {
        this.setData({ uploading: false });
      },
    });
  },
});
