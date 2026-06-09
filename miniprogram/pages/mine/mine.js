Page({
  data: {
    nickname: '',
    roleLabel: '',
    isAdmin: false,
  },
  onShow() {
    const user = getApp().globalData.user || {};
    const isAdmin = user.role === 'admin';
    this.setData({
      nickname: user.nickname || '未登录',
      roleLabel: isAdmin ? '管理员' : '普通用户',
      isAdmin,
    });
  },
  goMembers() {
    wx.navigateTo({ url: '/pages/medical/members/members' });
  },
  goAbout() {
    wx.navigateTo({ url: '/pages/about/about' });
  },
});
