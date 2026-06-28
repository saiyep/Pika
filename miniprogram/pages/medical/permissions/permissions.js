const { request } = require('../../../utils/request');

const ACTIONS = [
  { key: 'view_report', label: '可查看我的报告' },
  { key: 'upload_for_owner', label: '可代我上传' },
  { key: 'edit_report', label: '可编辑我的报告' },
  { key: 'delete_report', label: '可删除我的报告' },
];

function normalizeActions(actions) {
  return Array.isArray(actions) && actions.length ? actions : ACTIONS.map((a) => a.key);
}

function buildActionOptions(actions) {
  const picked = new Set(normalizeActions(actions));
  return ACTIONS.map((a) => ({ ...a, checked: picked.has(a.key) }));
}

Page({
  data: {
    loading: false,
    saving: false,
    members: [],
    memberLabels: [],
    grants: {},
    selectedMemberIndex: 0,
    selectedMemberId: null,
    draftActions: [],
    originalActions: [],
    actionOptions: buildActionOptions(ACTIONS.map((a) => a.key)),
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    this.setData({ loading: true });
    Promise.allSettled([
      request({ url: '/api/user/members' }),
      request({ url: '/api/medical/permissions' }),
    ])
      .then(([membersRes, aclRes]) => {
        const membersData = membersRes.status === 'fulfilled' ? membersRes.value : { items: [] };
        const aclData = aclRes.status === 'fulfilled' ? aclRes.value : { grants: [] };
        const ownerUserId = Number((aclData && aclData.owner_user_id) || 0);
        const grantsMap = {};
        (aclData.grants || []).forEach((g) => {
          grantsMap[Number(g.grantee_user_id)] = normalizeActions(g.actions);
        });

        const members = (membersData.items || [])
          .filter((m) => Number(m.id) !== ownerUserId && m.status !== 'disabled')
          .map((m) => ({
            ...m,
            id: Number(m.id),
            roleLabel: m.family_role === 'admin' ? '管理员' : '普通成员',
            initial: (m.nickname || ('用户' + m.id))[0],
          }));

        const selectedMemberIndex = 0;
        const selectedMember = members[selectedMemberIndex] || null;
        const selectedMemberId = selectedMember ? selectedMember.id : null;
        const selectedActions = selectedMemberId ? (grantsMap[selectedMemberId] || ACTIONS.map((a) => a.key)) : [];

        if (membersRes.status === 'rejected' || aclRes.status === 'rejected') {
          console.log('load permissions partial failure', {
            membersOk: membersRes.status === 'fulfilled',
            aclOk: aclRes.status === 'fulfilled',
          });
        }

        this.setData({
          members,
          memberLabels: members.map((m) => m.nickname || ('用户' + m.id)),
          grants: grantsMap,
          selectedMemberIndex,
          selectedMemberId,
          draftActions: [...selectedActions],
          originalActions: [...selectedActions],
          actionOptions: buildActionOptions(selectedActions),
        });
      })
      .catch((err) => {
        console.log('load permissions failed', err);
        wx.showToast({ title: '加载失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onMemberPick(e) {
    const selectedMemberIndex = Number(e.detail.value);
    const member = this.data.members[selectedMemberIndex] || null;
    const memberId = member ? Number(member.id) : null;
    const actions = memberId ? normalizeActions(this.data.grants[memberId]) : [];
    this.setData({
      selectedMemberIndex,
      selectedMemberId: memberId,
      draftActions: [...actions],
      originalActions: [...actions],
      actionOptions: buildActionOptions(actions),
    });
  },

  onToggleAction(e) {
    const action = e.currentTarget.dataset.action;
    const checked = !!e.detail.value;
    const current = new Set(this.data.draftActions || []);
    if (checked) current.add(action);
    else current.delete(action);
    const draftActions = Array.from(current);
    this.setData({ draftActions, actionOptions: buildActionOptions(draftActions) });
  },

  onCancelMember() {
    const actions = [...this.data.originalActions];
    this.setData({ draftActions: actions, actionOptions: buildActionOptions(actions) });
  },

  onSaveMember() {
    if (this.data.saving || !this.data.selectedMemberId) return;
    const memberId = Number(this.data.selectedMemberId);
    const actions = this.data.draftActions || [];
    this.setData({ saving: true });
    request({
      url: '/api/medical/permissions',
      method: 'PUT',
      data: { grantee_user_id: memberId, actions },
    })
      .then(() => {
        const grants = { ...this.data.grants, [memberId]: [...actions] };
        this.setData({
          grants,
          originalActions: [...actions],
          actionOptions: buildActionOptions(actions),
        });
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
