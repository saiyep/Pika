const { BASE_URL } = require('../../../config');
const { request } = require('../../../utils/request');

Page({
  data: {
    members: [],
    myId: null,
    isAdmin: false,

    actionVisible: false,
    actionMember: null,

    addVisible: false,
    adding: false,
    addNickname: '',
    addAvatarPath: '',
    addIsAdmin: false,

    editVisible: false,
    editingMemberId: null,
    editNickname: '',
    editAvatarPath: '',
    savingEdit: false,
  },
  noop() {},

  onShow() {
    const user = getApp().globalData.user || {};
    const isAdmin = user.family_role === 'admin' || user.role === 'admin';
    this.setData({ myId: user.id || null, isAdmin });
    this.load();
  },
  load() {
    request({ url: '/api/user/members' })
      .then((data) => {
        this.setData({ members: this.decorate(data.items || []) });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },
  decorate(items) {
    return items.map((m) => {
      const name = m.nickname || ('用户' + m.id);
      const role = m.family_role || m.role || 'member';
      const isActive = m.status !== 'disabled';
      return {
        ...m,
        role,
        isActive,
        roleLabel: role === 'admin' ? '管理员' : '普通成员',
        statusLabel: isActive ? '启用中' : '已停用',
        isMe: m.id === this.data.myId,
        avatarUrl: m.avatar_url ? BASE_URL + m.avatar_url : '',
        initial: name[0],
        menuLabelRole: role === 'admin' ? '设为普通成员' : '设为管理员',
        menuLabelActive: isActive ? '移除成员' : '恢复成员',
      };
    });
  },
  onOpenActions(e) {
    if (!this.data.isAdmin) return;
    const id = Number(e.currentTarget.dataset.id);
    const member = this.data.members.find((m) => m.id === id);
    if (!member) return;
    this.setData({ actionVisible: true, actionMember: member });
  },

  onCloseActions() {
    this.setData({ actionVisible: false, actionMember: null });
  },

  onActionEdit() {
    const member = this.data.actionMember;
    this.onCloseActions();
    if (!member) return;
    this.setData({
      editVisible: true,
      editingMemberId: member.id,
      editNickname: member.nickname || '',
      editAvatarPath: '',
    });
  },

  onActionToggleRole() {
    if (!this.data.isAdmin) return;
    const member = this.data.actionMember;
    this.onCloseActions();
    if (!member) return;
    const id = Number(member.id);
    const next = member.role === 'admin' ? 'member' : 'admin';
    wx.showModal({
      title: '修改角色',
      content: `确定将该成员设为${next === 'admin' ? '管理员' : '普通成员'}？`,
      success: (res) => {
        if (!res.confirm) return;
        request({ url: `/api/user/members/${id}/role`, method: 'PUT', data: { role: next } })
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

  onActionToggleActive() {
    if (!this.data.isAdmin) return;
    const member = this.data.actionMember;
    this.onCloseActions();
    if (!member) return;
    const id = Number(member.id);
    const next = !member.isActive;
    wx.showModal({
      title: next ? '恢复成员' : '移除成员',
      content: next ? '确认恢复该成员吗？' : '确认移除该成员吗？移除后不会删除历史检查单。',
      success: (res) => {
        if (!res.confirm) return;
        request({
          url: `/api/user/members/${id}/status`,
          method: 'PUT',
          data: { active: next },
        })
          .then(() => {
            this.load();
            wx.showToast({ title: next ? '已恢复' : '已移除', icon: 'success' });
          })
          .catch(() => {
            wx.showToast({ title: '操作失败', icon: 'none' });
          });
      },
    });
  },


  onEditNicknameInput(e) {
    this.setData({ editNickname: e.detail.value || '' });
  },

  onChooseMemberAvatar(e) {
    this.setData({ editAvatarPath: e.detail.avatarUrl || '' });
  },

  onCancelEdit() {
    this.setData({
      editVisible: false,
      editingMemberId: null,
      editNickname: '',
      editAvatarPath: '',
      savingEdit: false,
    });
  },

  onSaveEdit() {
    if (!this.data.isAdmin || this.data.savingEdit) return;
    const memberId = this.data.editingMemberId;
    const nickname = (this.data.editNickname || '').trim();
    if (!memberId || !nickname) {
      wx.showToast({ title: '昵称不能为空', icon: 'none' });
      return;
    }

    const avatarPath = this.data.editAvatarPath;
    this.setData({ savingEdit: true });

    const done = () => {
      this.onCancelEdit();
      this.load();
      wx.showToast({ title: '已保存', icon: 'success' });
    };

    if (avatarPath) {
      const token = (getApp().globalData && getApp().globalData.token) || wx.getStorageSync('token') || '';
      wx.uploadFile({
        url: `${BASE_URL}/api/user/members/${memberId}/profile`,
        filePath: avatarPath,
        name: 'avatar',
        formData: { nickname },
        header: { 'X-Pika-Token': token },
        success: (res) => {
          try {
            const body = JSON.parse(res.data);
            if (body && body.code === 0) done();
            else wx.showToast({ title: '保存失败', icon: 'none' });
          } catch (_e) {
            wx.showToast({ title: '保存失败', icon: 'none' });
          }
        },
        fail: () => wx.showToast({ title: '网络错误', icon: 'none' }),
        complete: () => this.setData({ savingEdit: false }),
      });
      return;
    }

    request({
      url: `/api/user/members/${memberId}/profile`,
      method: 'POST',
      data: { nickname },
      header: { 'content-type': 'application/x-www-form-urlencoded' },
    })
      .then(done)
      .catch(() => {
        wx.showToast({ title: '保存失败', icon: 'none' });
      })
      .finally(() => this.setData({ savingEdit: false }));
  },

  onOpenAdd() {
    if (!this.data.isAdmin) return;
    this.setData({
      addVisible: true,
      addNickname: '',
      addAvatarPath: '',
      addIsAdmin: false,
    });
  },

  onCloseAdd() {
    this.setData({
      addVisible: false,
      adding: false,
      addNickname: '',
      addAvatarPath: '',
      addIsAdmin: false,
    });
  },

  onAddNicknameInput(e) {
    this.setData({ addNickname: (e.detail.value || '').trim() });
  },

  onAddChooseAvatar(e) {
    this.setData({ addAvatarPath: e.detail.avatarUrl || '' });
  },

  onAddAdminSwitch(e) {
    this.setData({ addIsAdmin: !!e.detail.value });
  },

  onSubmitAdd() {
    if (!this.data.isAdmin || this.data.adding) return;
    const nickname = this.data.addNickname;
    if (!nickname) {
      wx.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }

    this.setData({ adding: true });

    let createdId = null;
    request({
      url: '/api/user/members',
      method: 'POST',
      data: { nickname },
    })
      .then((member) => {
        createdId = member.id;
        if (!createdId) throw new Error('missing member id');
        if (!this.data.addAvatarPath) return null;

        const token = (getApp().globalData && getApp().globalData.token) || wx.getStorageSync('token') || '';
        return new Promise((resolve, reject) => {
          wx.uploadFile({
            url: `${BASE_URL}/api/user/members/${createdId}/profile`,
            filePath: this.data.addAvatarPath,
            name: 'avatar',
            formData: { nickname },
            header: { 'X-Pika-Token': token },
            success: (res) => {
              try {
                const body = JSON.parse(res.data);
                if (body && body.code === 0) resolve(body.data);
                else reject(new Error((body && body.msg) || 'avatar upload failed'));
              } catch (_e) {
                reject(new Error('avatar upload parse failed'));
              }
            },
            fail: () => reject(new Error('avatar upload network failed')),
          });
        });
      })
      .then(() => {
        if (!this.data.addIsAdmin || !createdId) return;
        return request({
          url: `/api/user/members/${createdId}/role`,
          method: 'PUT',
          data: { role: 'admin' },
        });
      })
      .then(() => {
        this.onCloseAdd();
        this.load();
        wx.showToast({ title: '成员已添加', icon: 'success' });
      })
      .catch(() => {
        wx.showToast({ title: '新增失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ adding: false });
      });
  },
});
