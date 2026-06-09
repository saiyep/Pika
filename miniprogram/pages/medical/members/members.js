const { request } = require('../../../utils/request');

Page({
  data: {
    members: [],
    myId: null,
  },
  onShow() {
    const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
    this.setData({ myId });
    request({ url: '/api/medical/members' })
      .then((data) => {
        this.setData({ members: data.items || [] });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },
});
