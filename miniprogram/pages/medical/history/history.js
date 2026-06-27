const { request } = require('../../../utils/request');

const TIME_RANGES = ['过去1个月', '过去3个月', '过去半年', '过去1年', '自定义'];
const DEFAULT_TIME_INDEX = 1;
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
    members: [],
    subjectLabels: [],
    subjectIndex: 0,
    hospitals: [],
    selectedHospitals: [],
    hospitalPanelOpen: false,
    timeRanges: TIME_RANGES,
    timeIndex: DEFAULT_TIME_INDEX,
    customFrom: '',
    customTo: '',
    showCustom: false,
  },
  onShow() {
    this.bootstrap();
  },
  bootstrap() {
    Promise.all([
      request({ url: '/api/user/members' }).catch(() => ({ items: [] })),
      request({ url: '/api/medical/hospitals' }).catch(() => []),
    ]).then(([m, hospitals]) => {
      const members = m.items || [];
      const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
      let sidx = members.findIndex((x) => x.id === myId);
      sidx = sidx < 0 ? 0 : sidx;
      this.setData(
        {
          members,
          subjectLabels: members.map((x) => x.nickname || ('用户' + x.id)),
          subjectIndex: sidx,
          hospitals: hospitals || [],
          timeIndex: DEFAULT_TIME_INDEX,
          showCustom: false,
        },
        () => {
          if (members.length) this.load();
          else this.setData({ items: [] });
        }
      );
    });
  },

  currentSubjectId() {
    const m = this.data.members[this.data.subjectIndex];
    return m ? m.id : null;
  },

  selectedHospitalSummary() {
    const count = this.data.selectedHospitals.length;
    if (!count) return '全部医院';
    if (count === 1) return this.data.selectedHospitals[0];
    return `已选 ${count} 家医院`;
  },

  isHospitalSelected(name) {
    return this.data.selectedHospitals.includes(name);
  },

  onSubjectPick(e) {
    this.setData({ subjectIndex: Number(e.detail.value) }, () => this.load());
  },
  onTimePick(e) {
    const idx = Number(e.detail.value);
    this.setData({ timeIndex: idx, showCustom: idx === CUSTOM_INDEX }, () => {
      if (idx !== CUSTOM_INDEX) this.load();
    });
  },
  toggleHospitalPanel() {
    this.setData({ hospitalPanelOpen: !this.data.hospitalPanelOpen });
  },
  onHospitalToggle(e) {
    const hospital = e.currentTarget.dataset.hospital;
    if (!hospital) return;
    const selected = new Set(this.data.selectedHospitals);
    if (selected.has(hospital)) selected.delete(hospital);
    else selected.add(hospital);
    this.setData({ selectedHospitals: Array.from(selected) }, () => this.load());
  },
  clearHospitals() {
    this.setData({ selectedHospitals: [] }, () => this.load());
  },
  onCustomFrom(e) {
    this.setData({ customFrom: e.detail.value }, () => this.load());
  },
  onCustomTo(e) {
    this.setData({ customTo: e.detail.value }, () => this.load());
  },

  buildQuery() {
    const parts = ['page=1', 'size=50'];
    const subjectId = this.currentSubjectId();
    if (subjectId) {
      parts.push('subject_id=' + subjectId);
    }
    this.data.selectedHospitals.forEach((hospital) => {
      parts.push('hospital=' + encodeURIComponent(hospital));
    });
    const ti = this.data.timeIndex;
    if (ti >= 0 && ti <= 3) {
      const map = { 0: 1, 1: 3, 2: 6, 3: 12 };
      parts.push('date_from=' + monthsAgo(map[ti]));
    } else if (ti === CUSTOM_INDEX) {
      if (this.data.customFrom) parts.push('date_from=' + this.data.customFrom);
      if (this.data.customTo) parts.push('date_to=' + this.data.customTo);
    }
    return parts.join('&');
  },

  load() {
    if (!this.currentSubjectId()) {
      this.setData({ items: [] });
      return;
    }
    request({ url: '/api/medical/reports?' + this.buildQuery() })
      .then((data) => {
        this.setData({ items: data.items });
      })
      .catch((err) => {
        if (err && err.code === 403) {
          this.setData({ items: [] });
          return;
        }
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
