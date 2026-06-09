const { request } = require('../../../utils/request');

Page({
  data: {
    items: [],
    // 被检查人 filter：第 0 项是"全家"，其余是各成员
    filterLabels: ['全家'],
    members: [],
    filterIndex: 0,
  },
  onShow() {
    this.loadMembers();
  },
  loadMembers() {
    request({ url: '/api/medical/members' })
      .then((data) => {
        const members = data.items || [];
        const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
        // 默认选中"自己"；找不到则退回"全家"。
        let idx = members.findIndex((m) => m.id === myId);
        idx = idx < 0 ? 0 : idx + 1; // +1 因为第 0 项是"全家"
        this.setData(
          {
            members,
            filterLabels: ['全家', ...members.map((m) => m.nickname || ('用户' + m.id))],
            filterIndex: idx,
          },
          () => this.load()
        );
      })
      .catch(() => {
        this.load();
      });
  },
  onFilterPick(e) {
    this.setData({ filterIndex: Number(e.detail.value) }, () => this.load());
  },
  load() {
    let url = '/api/medical/reports?page=1&size=50';
    if (this.data.filterIndex > 0) {
      const m = this.data.members[this.data.filterIndex - 1];
      if (m) url += '&subject_id=' + m.id;
    }
    request({ url })
      .then((data) => {
        this.setData({ items: data.items });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },
  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/pages/medical/report-detail/report-detail?id=' + id });
  },
  onDelete(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除记录',
      content: '确定删除这条检查记录？原图和数据将一并删除，不可恢复。',
      confirmColor: '#e64340',
      success: (res) => {
        if (!res.confirm) return;
        request({ url: `/api/medical/reports/${id}`, method: 'DELETE' })
          .then(() => {
            this.setData({ items: this.data.items.filter((it) => it.id !== id) });
            wx.showToast({ title: '已删除', icon: 'success' });
          })
          .catch(() => {
            wx.showToast({ title: '删除失败', icon: 'none' });
          });
      },
    });
  },
});
