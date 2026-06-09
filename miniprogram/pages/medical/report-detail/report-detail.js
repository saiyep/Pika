const { request } = require('../../../utils/request');
const { BASE_URL } = require('../../../config');

const PRESET_HOSPITALS = ['北京大学国际医院', '北京协和医院', '北京积水潭医院', '北京大学肿瘤医院'];
const HOSPITAL_OPTIONS = [...PRESET_HOSPITALS, '其他（可输入）'];
const OTHER_INDEX = PRESET_HOSPITALS.length;

function matchHospital(name) {
  if (!name) return { index: OTHER_INDEX, custom: '' };
  for (let i = 0; i < PRESET_HOSPITALS.length; i++) {
    const key = PRESET_HOSPITALS[i].replace(/^北京/, '');
    if (name.indexOf(key) >= 0 || name.indexOf(PRESET_HOSPITALS[i]) >= 0) {
      return { index: i, custom: '' };
    }
  }
  return { index: OTHER_INDEX, custom: name };
}

Page({
  data: {
    report: {},
    metrics: [],
    imageUrl: '',
    reportId: '',
    uploadedAt: '',
    reparsing: false,
    editing: false,
    saving: false,
    // edit-mode fields
    editLabel: '',
    editDate: '',
    editMetrics: [],
    hospitalOptions: HOSPITAL_OPTIONS,
    hospitalIndex: OTHER_INDEX,
    hospitalCustom: '',
    // 被检查者
    members: [],
    memberLabels: [],
    subjectIndex: 0,
  },
  onLoad(query) {
    const id = query.id;
    this.setData({ reportId: id, imageUrl: BASE_URL + '/api/medical/reports/' + id + '/image' });
    this.loadMembers();
    this.load();
  },
  loadMembers() {
    request({ url: '/api/user/members' })
      .then((data) => {
        const members = data.items || [];
        this.setData({ members, memberLabels: members.map((m) => m.nickname || ('用户' + m.id)) });
      })
      .catch(() => {});
  },
  load() {
    request({ url: '/api/medical/reports/' + this.data.reportId })
      .then((data) => {
        this.setData({
          report: data.report,
          metrics: data.metrics,
          uploadedAt: this.fmtTime(data.report.created_at),
        });
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },
  fmtTime(s) {
    if (!s) return '';
    // 后端 created_at 形如 "2026-06-09T08:30:00"，截到分钟，空格分隔
    return String(s).replace('T', ' ').slice(0, 16);
  },
  previewImage() {
    if (this.data.imageUrl) {
      wx.previewImage({ urls: [this.data.imageUrl] });
    }
  },

  enterEdit() {
    const r = this.data.report;
    const matched = matchHospital(r.hospital);
    let sidx = this.data.members.findIndex((m) => m.id === r.subject_id);
    if (sidx < 0) sidx = 0;
    this.setData({
      editing: true,
      editLabel: r.report_type_label || '',
      editDate: r.report_date || '',
      editMetrics: this.data.metrics.map((m) => ({
        item_name: m.item_name,
        item_code: m.item_code,
        value_text: m.value_text,
        unit: m.unit,
        ref_range: m.ref_range,
        abnormal_flag: m.abnormal_flag,
      })),
      hospitalIndex: matched.index,
      hospitalCustom: matched.custom,
      subjectIndex: sidx,
    });
  },
  cancelEdit() {
    this.setData({ editing: false });
  },

  resolvedHospital() {
    return this.data.hospitalIndex === OTHER_INDEX
      ? this.data.hospitalCustom
      : PRESET_HOSPITALS[this.data.hospitalIndex];
  },
  onHospitalPick(e) {
    this.setData({ hospitalIndex: Number(e.detail.value) });
  },
  onHospitalCustomInput(e) {
    this.setData({ hospitalCustom: e.detail.value || '' });
  },
  onSubjectPick(e) {
    this.setData({ subjectIndex: Number(e.detail.value) });
  },
  subjectId() {
    const m = this.data.members[this.data.subjectIndex];
    return m ? m.id : null;
  },
  onLabelInput(e) {
    this.setData({ editLabel: e.detail.value || '' });
  },
  onDateInput(e) {
    this.setData({ editDate: e.detail.value || '' });
  },
  onMetricFieldInput(e) {
    const { idx, field } = e.currentTarget.dataset;
    const editMetrics = [...this.data.editMetrics];
    editMetrics[idx] = { ...editMetrics[idx], [field]: e.detail.value };
    this.setData({ editMetrics });
  },

  saveEdit() {
    if (this.data.saving) return;
    this.setData({ saving: true });
    const label = this.data.editLabel || null;
    request({
      url: `/api/medical/reports/${this.data.reportId}`,
      method: 'PUT',
      data: {
        report_type: label ? 'custom' : this.data.report.report_type,
        report_type_label: label,
        report_date: this.data.editDate || null,
        hospital: this.resolvedHospital() || null,
        subject_id: this.subjectId(),
        metrics: this.data.editMetrics,
      },
    })
      .then((data) => {
        this.setData({
          report: data.report,
          metrics: data.metrics,
          editing: false,
          uploadedAt: this.fmtTime(data.report.created_at),
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

  onReparse() {
    if (this.data.reparsing) return;
    this.setData({ reparsing: true });
    request({ url: `/api/medical/reports/${this.data.reportId}/reparse`, method: 'POST' })
      .then((data) => {
        this.setData({ report: data.report, metrics: data.metrics });
        const ok = data.report.status === 'parsed';
        wx.showToast({ title: ok ? '解析成功' : '仍未识别到数据', icon: ok ? 'success' : 'none' });
      })
      .catch((err) => {
        wx.showToast({ title: (err && err.message) || '重新解析失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ reparsing: false });
      });
  },
});
