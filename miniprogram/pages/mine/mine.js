const { BASE_URL } = require('../../config');
const { request } = require('../../utils/request');
const { login, clearSession, isLoggedIn, ensureLoginWithModal, getToken } = require('../../utils/auth');

Page({
  data: {
    loggedIn: false,
    loggingIn: false,
    editing: false,
    user: {},
    nickname: '未登录',
    initial: '?',
    roleLabel: '',
    isAdmin: false,
    avatarUrl: '',
    editNickname: '',
    pendingAvatar: '',
  },

  onShow() {
    if (!isLoggedIn()) {
      this.setLoggedOutState();
      return;
    }
    this.refresh();
  },

  setLoggedOutState() {
    this.setData({
      loggedIn: false,
      loggingIn: false,
      editing: false,
      user: {},
      nickname: '未登录',
      initial: '?',
      roleLabel: '',
      isAdmin: false,
      avatarUrl: '',
      editNickname: '',
      pendingAvatar: '',
    });
  },

  refresh() {
    request({ url: '/api/user/whoami' })
      .then((user) => {
        const safeUser = user && typeof user === 'object' ? user : {};
        this.apply(safeUser);
      })
      .catch((err) => {
        if (err && err.code === 401) {
          this.setLoggedOutState();
          return;
        }
        wx.showToast({ title: '刷新失败', icon: 'none' });
      });
  },

  apply(user) {
    const safeUser = user && typeof user === 'object' ? user : {};
    const hasUser = !!safeUser.id;
    if (!hasUser) {
      this.setLoggedOutState();
      return;
    }
    const isAdmin = safeUser.role === 'admin';
    const name = safeUser.nickname || '微信用户';
    getApp().globalData.user = safeUser;
    this.setData({
      loggedIn: true,
      editing: false,
      user: safeUser,
      nickname: name,
      initial: name[0] || '?',
      roleLabel: isAdmin ? '管理员' : '普通用户',
      isAdmin,
      avatarUrl: safeUser.avatar_url ? BASE_URL + safeUser.avatar_url + '?t=' + Date.now() : '',
      editNickname: safeUser.nickname || '',
      pendingAvatar: '',
    });
  },

  doWechatLogin() {
    if (this.data.loggingIn) return;
    this.setData({ loggingIn: true });
    login()
      .then((res) => {
        this.apply((res && res.user) || {});
        wx.showToast({ title: '登录成功', icon: 'success' });
      })
      .catch((err) => {
        console.error('login failed', err, BASE_URL);
        const raw = (err && (err.msg || err.errMsg)) || (typeof err === 'string' ? err : '登录失败');
        const msg = String(raw).slice(0, 120);
        wx.showModal({
          title: '登录失败',
          content: msg,
          showCancel: false,
        });
      })
      .finally(() => this.setData({ loggingIn: false }));
  },

  startEdit() {
    if (!this.data.loggedIn) {
      ensureLoginWithModal();
      return;
    }
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
    this.setData({ pendingAvatar: e.detail.avatarUrl });
  },

  onNicknameInput(e) {
    this.setData({ editNickname: e.detail.value || '' });
  },

  saveProfile() {
    const token = getToken();
    if (!token) {
      ensureLoginWithModal();
      return;
    }

    const nickname = this.data.editNickname || '';
    const avatar = this.data.pendingAvatar;

    const finish = (updatedUser) => {
      if (updatedUser && typeof updatedUser === 'object' && updatedUser.id) {
        this.apply(updatedUser);
      } else {
        this.setData({ editing: false, pendingAvatar: '' });
      }
      this.refresh();
      wx.showToast({ title: '已保存', icon: 'success' });
    };

    if (avatar) {
      wx.uploadFile({
        url: BASE_URL + '/api/user/profile',
        filePath: avatar,
        name: 'avatar',
        formData: { nickname },
        header: { 'X-Pika-Token': token },
        success: (res) => {
          try {
            const body = JSON.parse(res.data);
            if (body && body.code === 0) finish(body.data);
            else wx.showToast({ title: '保存失败', icon: 'none' });
          } catch (_e) {
            wx.showToast({ title: '保存失败', icon: 'none' });
          }
        },
        fail: () => wx.showToast({ title: '网络错误', icon: 'none' }),
      });
      return;
    }

    wx.request({
      url: BASE_URL + '/api/user/profile',
      method: 'POST',
      header: {
        'X-Pika-Token': token,
        'content-type': 'application/x-www-form-urlencoded',
      },
      data: { nickname },
      success: (res) => {
        if (res.data && res.data.code === 0) finish(res.data.data);
        else wx.showToast({ title: '保存失败', icon: 'none' });
      },
      fail: () => wx.showToast({ title: '网络错误', icon: 'none' }),
    });
  },

  goMembers() {
    if (!this.data.loggedIn) {
      ensureLoginWithModal();
      return;
    }
    wx.navigateTo({ url: '/pages/medical/members/members' });
  },

  scanJoinMember() {
    if (!this.data.loggedIn) {
      ensureLoginWithModal();
      return;
    }
    wx.navigateTo({ url: '/pages/medical/members/members?scan=1' });
  },

  goAbout() {
    wx.navigateTo({ url: '/pages/about/about' });
  },

  logout() {
    wx.showModal({
      title: '退出登录',
      content: '确认退出当前账号吗？',
      confirmText: '退出',
      success: (res) => {
        if (!res.confirm) return;
        clearSession();
        this.setLoggedOutState();
        wx.showToast({ title: '已退出登录', icon: 'none' });
      },
    });
  },
});