const { BASE_URL } = require('../../config');
const { request } = require('../../utils/request');

Page({
  data: {
    user: {},
    nickname: '',
    initial: '?',
    roleLabel: '',
    isAdmin: false,
    avatarUrl: '',
    editing: false,
    editNickname: '',
    pendingAvatar: '', // 本地临时头像路径，保存时上传
  },
  onShow() {
    this.refresh();
  },
  refresh() {
    request({ url: '/api/user/whoami' })
      .then((user) => {
        getApp().globalData.user = user;
        this.apply(user);
      })
      .catch(() => {
        this.apply(getApp().globalData.user || {});
      });
  },
  apply(user) {
    const isAdmin = user.role === 'admin';
    const hasUser = !!(user && user.id);
    const name = user.nickname || (hasUser ? '家庭成员' : '未登录');
    this.setData({
      user,
      nickname: name,
      initial: name[0] || '?',
      roleLabel: isAdmin ? '管理员' : '普通用户',
      isAdmin,
      avatarUrl: user.avatar_url ? BASE_URL + user.avatar_url + '?t=' + Date.now() : '',
    });
  },

  startEdit() {
    this.setData({
      editing: true,
      editNickname: this.data.user.nickname || '',
      pendingAvatar: '',
    });
  },
  cancelEdit() {
    this.setData({ editing: false, pendingAvatar: '' });
  },
  onChooseAvatar(e) {
    // 微信返回临时头像路径
    this.setData({ pendingAvatar: e.detail.avatarUrl });
  },
  onNicknameInput(e) {
    this.setData({ editNickname: e.detail.value || '' });
  },
  saveProfile() {
    const token = getApp().globalData.token || wx.getStorageSync('token') || '';
    const nickname = this.data.editNickname || '';
    const avatar = this.data.pendingAvatar;

    const finish = () => {
      this.setData({ editing: false, pendingAvatar: '' });
      this.refresh();
      wx.showToast({ title: '已保存', icon: 'success' });
    };

    if (avatar) {
      // 有新头像：用 uploadFile 带文件 + 昵称
      wx.uploadFile({
        url: BASE_URL + '/api/user/profile',
        filePath: avatar,
        name: 'avatar',
        formData: { nickname },
        header: { 'X-Pika-Token': token },
        success: (res) => {
          try {
            const body = JSON.parse(res.data);
            if (body.code === 0) finish();
            else wx.showToast({ title: '保存失败', icon: 'none' });
          } catch (_e) {
            wx.showToast({ title: '保存失败', icon: 'none' });
          }
        },
        fail: () => wx.showToast({ title: '网络错误', icon: 'none' }),
      });
    } else {
      // 只改昵称：后端是 Form 字段，用表单编码发送
      wx.request({
        url: BASE_URL + '/api/user/profile',
        method: 'POST',
        header: {
          'X-Pika-Token': token,
          'content-type': 'application/x-www-form-urlencoded',
        },
        data: { nickname },
        success: (res) => {
          if (res.data && res.data.code === 0) finish();
          else wx.showToast({ title: '保存失败', icon: 'none' });
        },
        fail: () => wx.showToast({ title: '网络错误', icon: 'none' }),
      });
    }
  },

  goMembers() {
    wx.navigateTo({ url: '/pages/medical/members/members' });
  },
  goAbout() {
    wx.navigateTo({ url: '/pages/about/about' });
  },
});
