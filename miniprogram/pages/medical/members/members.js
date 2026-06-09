const { request } = require('../../../utils/request');

Page({
  data: {
    members: [],
    myId: null,
    isAdmin: false,
  },
  onShow() {
    const user = getApp().globalData.user || {};
    this.setData({ myId: user.id || null, isAdmin: user.role === 'admin' });
    this.load();
  },
  load() {
    request({ url: '/api/medical/members' })
      .then((data) => {
        this.setData({ members: this.decorate(data.items || []) });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },
  decorate(items) {
    return items.map((m) => ({
      ...m,
      roleLabel: m.role === 'admin' ? '管理员' : '普通用户',
      isMe: m.id === this.data.myId,
    }));
  },
  onToggleRole(e) {
    const id = Number(e.currentTarget.dataset.id);
    const cur = e.currentTarget.dataset.role;
    const next = cur === 'admin' ? 'user' : 'admin';
    wx.showModal({
      title: '修改角色',
      content: `确定将该成员设为${next === 'admin' ? '管理员' : '普通用户'}？`,
      success: (res) => {
        if (!res.confirm) return;
        request({ url: `/api/medical/members/${id}/role`, method: 'PUT', data: { role: next } })
          .then(() => {
            this.load();
            wx.showToast({ title: '已修改', icon: 'success' });
          })
          .catch(() => {
            wx.showToast({ title: '修改失败', icon: 'none' });
          });
      },
    });
  },
});
