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
    rawItems: [],
    members: [],
    subjectLabels: [],
    subjectIndex: 0,
    memberDisplay: '选择成员',
    hospitals: [],
    hospitalOptions: [],
    selectedHospitals: [],
    hospitalPanelOpen: false,
    hospitalDisplay: '无可选医院',
    timeRanges: TIME_RANGES,
    timeIndex: DEFAULT_TIME_INDEX,
    timeDisplay: TIME_RANGES[DEFAULT_TIME_INDEX],
    customFrom: '',
    customTo: '',
    showCustom: false,
  },

  formatMemberDisplay(subjectLabels, subjectIndex) {
    return subjectLabels.length ? (subjectLabels[subjectIndex] || '选择成员') : '选择成员';
  },

  formatTimeDisplay(timeIndex, customFrom, customTo, timeRanges) {
    if (timeIndex === CUSTOM_INDEX) {
      if (customFrom && customTo) return `${customFrom} 至 ${customTo}`;
      if (customFrom) return `${customFrom} 起`;
      if (customTo) return `截至 ${customTo}`;
      return '自定义';
    }
    return timeRanges[timeIndex] || TIME_RANGES[DEFAULT_TIME_INDEX];
  },

  formatHospitalDisplay(hospitals, selectedHospitals) {
    const total = hospitals.length;
    const count = selectedHospitals.length;
    if (!total) return '无可选医院';
    if (!count) return `全部医院（${total}）`;
    return `已选 ${count}/${total}`;
  },

  buildHospitalOptions(hospitals, selectedHospitals) {
    const selectedSet = new Set(selectedHospitals || []);
    return (hospitals || []).map((name) => ({ name, selected: selectedSet.has(name) }));
  },

  onShow() {
    this.bootstrap();
  },

  bootstrap() {
    request({ url: '/api/user/members' })
      .catch(() => ({ items: [] }))
      .then((m) => {
        const members = m.items || [];
        const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
        let sidx = members.findIndex((x) => x.id === myId);
        sidx = sidx < 0 ? 0 : sidx;
        const subjectLabels = members.map((x) => x.nickname || ('用户' + x.id));
        const initialState = {
          members,
          subjectLabels,
          subjectIndex: sidx,
          hospitals: [],
          selectedHospitals: [],
          hospitalPanelOpen: false,
          timeIndex: DEFAULT_TIME_INDEX,
          showCustom: false,
        };
        this.setData(
          { ...initialState, ...this.refreshDisplay(initialState) },
          () => {
            if (members.length) this.load();
            else {
              const next = { rawItems: [], items: [], hospitals: [], hospitalOptions: [], selectedHospitals: [] };
              this.setData({ ...next, ...this.refreshDisplay(next) });
            }
          }
        );
      });
  },

  currentSubjectId() {
    const m = this.data.members[this.data.subjectIndex];
    return m ? m.id : null;
  },

  refreshDisplay(partial = {}) {
    const subjectLabels = partial.subjectLabels || this.data.subjectLabels;
    const subjectIndex = partial.subjectIndex !== undefined ? partial.subjectIndex : this.data.subjectIndex;
    const timeRanges = partial.timeRanges || this.data.timeRanges;
    const timeIndex = partial.timeIndex !== undefined ? partial.timeIndex : this.data.timeIndex;
    const customFrom = partial.customFrom !== undefined ? partial.customFrom : this.data.customFrom;
    const customTo = partial.customTo !== undefined ? partial.customTo : this.data.customTo;
    const hospitals = partial.hospitals || this.data.hospitals;
    const selectedHospitals = partial.selectedHospitals || this.data.selectedHospitals;
    return {
      memberDisplay: this.formatMemberDisplay(subjectLabels, subjectIndex),
      timeDisplay: this.formatTimeDisplay(timeIndex, customFrom, customTo, timeRanges),
      hospitalDisplay: this.formatHospitalDisplay(hospitals, selectedHospitals),
      hospitalOptions: this.buildHospitalOptions(hospitals, selectedHospitals),
    };
  },

  onSubjectPick(e) {
    const next = { subjectIndex: Number(e.detail.value), selectedHospitals: [], hospitalPanelOpen: false };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.load());
  },

  onTimePick(e) {
    const idx = Number(e.detail.value);
    const next = { timeIndex: idx, showCustom: idx === CUSTOM_INDEX, selectedHospitals: [], hospitalPanelOpen: false };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => {
      this.load();
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
    const next = { selectedHospitals: Array.from(selected) };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.applyHospitalFilter());
  },

  clearHospitals() {
    const next = { selectedHospitals: [] };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.applyHospitalFilter());
  },

  onCustomFrom(e) {
    const next = { customFrom: e.detail.value, selectedHospitals: [], hospitalPanelOpen: false };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.load());
  },

  onCustomTo(e) {
    const next = { customTo: e.detail.value, selectedHospitals: [], hospitalPanelOpen: false };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.load());
  },

  buildQuery() {
    const parts = ['page=1', 'size=50'];
    const subjectId = this.currentSubjectId();
    if (subjectId) {
      parts.push('subject_id=' + subjectId);
    }
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

  collectHospitals(items) {
    const set = new Set();
    (items || []).forEach((item) => {
      const hospital = item && item.hospital;
      if (hospital) set.add(hospital);
    });
    return Array.from(set);
  },

  applyHospitalFilter() {
    const selected = this.data.selectedHospitals;
    const rawItems = this.data.rawItems || [];
    if (!selected.length) {
      this.setData({ items: rawItems });
      return;
    }
    const picked = new Set(selected);
    const items = rawItems.filter((item) => picked.has(item.hospital));
    this.setData({ items });
  },

  load() {
    if (!this.currentSubjectId()) {
      const next = { rawItems: [], items: [], hospitals: [], hospitalOptions: [], selectedHospitals: [] };
      this.setData({ ...next, ...this.refreshDisplay(next) });
      return;
    }
    request({ url: '/api/medical/reports?' + this.buildQuery() })
      .then((data) => {
        const rawItems = data.items || [];
        const hospitals = this.collectHospitals(rawItems);
        const validSet = new Set(hospitals);
        const selectedHospitals = this.data.selectedHospitals.filter((h) => validSet.has(h));
        const next = { rawItems, hospitals, selectedHospitals };
        this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.applyHospitalFilter());
      })
      .catch((err) => {
        if (err && err.code === 403) {
          const next = { rawItems: [], items: [], hospitals: [], hospitalOptions: [], selectedHospitals: [] };
          this.setData({ ...next, ...this.refreshDisplay(next) });
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
            const rawItems = (this.data.rawItems || []).filter((it) => it.id !== id);
            const hospitals = this.collectHospitals(rawItems);
            const validSet = new Set(hospitals);
            const selectedHospitals = this.data.selectedHospitals.filter((h) => validSet.has(h));
            const next = { rawItems, hospitals, selectedHospitals };
        this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.applyHospitalFilter());
            wx.showToast({ title: '已删除', icon: 'success' });
          })
          .catch(() => {
            wx.showToast({ title: '删除失败', icon: 'none' });
          });
      },
    });
  },
});