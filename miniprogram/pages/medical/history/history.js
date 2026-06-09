const { request } = require('../../../utils/request');

const TIME_RANGES = ['全部时间', '过去1个月', '过去3个月', '过去半年', '过去1年', '自定义'];
const CUSTOM_INDEX = TIME_RANGES.length - 1;

function pad(n) {
  return n < 10 ? '0' + n : '' + n;
}
function ymd(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
function monthsAgo(n) {
  const d = new Date();
  d.setMonth(d.getMonth() - n);
  return ymd(d);
}

Page({
  data: {
    items: [],
    // 被检查者
    members: [],
    subjectLabels: ['全家'],
    subjectIndex: 0,
    // 医院
    hospitals: [],
    hospitalLabels: ['全部医院'],
    hospitalIndex: 0,
    // 时间范围
    timeRanges: TIME_RANGES,
    timeIndex: 0,
    customFrom: '',
    customTo: '',
    showCustom: false,
  },
  onShow() {
    this.bootstrap();
  },
  bootstrap() {
    // 拉成员 + 医院，然后加载列表
    Promise.all([
      request({ url: '/api/user/members' }).catch(() => ({ items: [] })),
      request({ url: '/api/medical/hospitals' }).catch(() => []),
    ]).then(([m, hospitals]) => {
      const members = m.items || [];
      const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
      let sidx = members.findIndex((x) => x.id === myId);
      sidx = sidx < 0 ? 0 : sidx + 1;
      this.setData(
        {
          members,
          subjectLabels: ['全家', ...members.map((x) => x.nickname || ('用户' + x.id))],
          subjectIndex: sidx,
          hospitals: hospitals || [],
          hospitalLabels: ['全部医院', ...(hospitals || [])],
        },
        () => this.load()
      );
    });
  },

  onSubjectPick(e) {
    this.setData({ subjectIndex: Number(e.detail.value) }, () => this.load());
  },
  onHospitalPick(e) {
    this.setData({ hospitalIndex: Number(e.detail.value) }, () => this.load());
  },
  onTimePick(e) {
    const idx = Number(e.detail.value);
    this.setData({ timeIndex: idx, showCustom: idx === CUSTOM_INDEX }, () => {
      if (idx !== CUSTOM_INDEX) this.load();
    });
  },
  onCustomFrom(e) {
    this.setData({ customFrom: e.detail.value }, () => this.load());
  },
  onCustomTo(e) {
    this.setData({ customTo: e.detail.value }, () => this.load());
  },

  buildQuery() {
    const parts = ['page=1', 'size=50'];
    if (this.data.subjectIndex > 0) {
      const m = this.data.members[this.data.subjectIndex - 1];
      if (m) parts.push('subject_id=' + m.id);
    }
    if (this.data.hospitalIndex > 0) {
      parts.push('hospital=' + encodeURIComponent(this.data.hospitalLabels[this.data.hospitalIndex]));
    }
    const ti = this.data.timeIndex;
    if (ti >= 1 && ti <= 4) {
      const map = { 1: 1, 2: 3, 3: 6, 4: 12 };
      parts.push('date_from=' + monthsAgo(map[ti]));
    } else if (ti === CUSTOM_INDEX) {
      if (this.data.customFrom) parts.push('date_from=' + this.data.customFrom);
      if (this.data.customTo) parts.push('date_to=' + this.data.customTo);
    }
    return parts.join('&');
  },

  load() {
    request({ url: '/api/medical/reports?' + this.buildQuery() })
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
