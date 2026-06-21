const { request } = require('../../../utils/request');

const ACTIONS = [
  { key: 'view_report', label: '可查看我的报告' },
  { key: 'upload_for_owner', label: '可代我上传' },
  { key: 'edit_report', label: '可编辑我的报告' },
  { key: 'delete_report', label: '可删除我的报告' },
];

Page({
  data: {
    loading: false,
    saving: false,
    myId: null,
    members: [],
    grants: {},
  },

  onShow() {
    const user = getApp().globalData.user || {};
    this.setData({ myId: user.id || null });
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });
    Promise.all([
      request({ url: '/api/user/members' }),
      request({ url: '/api/medical/permissions' }),
    ])
      .then(([membersData, aclData]) => {
        const myId = this.data.myId;
        const grantsMap = {};
        (aclData.grants || []).forEach((g) => {
          grantsMap[g.grantee_user_id] = g.actions || [];
        });

        const members = (membersData.items || [])
          .filter((m) => m.id !== myId && m.status !== 'disabled')
          .map((m) => {
            const actions = grantsMap[m.id] || [];
            return {
              ...m,
              actionItems: ACTIONS.map((a) => ({
                ...a,
                checked: actions.indexOf(a.key) >= 0,
              })),
            };
          });

        this.setData({ members, grants: grantsMap });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onToggleAction(e) {
    const memberId = Number(e.currentTarget.dataset.memberId);
    const action = e.currentTarget.dataset.action;
    const checked = !!e.detail.value;

    const members = this.data.members.map((m) => {
      if (m.id !== memberId) return m;
      const actionItems = m.actionItems.map((item) =>
        item.key === action ? { ...item, checked } : item
      );
      return { ...m, actionItems };
    });

    this.setData({ members });
  },

  onSaveMember(e) {
    if (this.data.saving) return;
    const memberId = Number(e.currentTarget.dataset.memberId);
    const member = this.data.members.find((m) => m.id === memberId);
    if (!member) return;

    const actions = member.actionItems.filter((i) => i.checked).map((i) => i.key);
    this.setData({ saving: true });
    request({
      url: '/api/medical/permissions',
      method: 'PUT',
      data: { grantee_user_id: memberId, actions },
    })
      .then(() => {
        wx.showToast({ title: '已保存', icon: 'success' });
      })
      .catch(() => {
        wx.showToast({ title: '保存失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ saving: false });
      });
  },
});
