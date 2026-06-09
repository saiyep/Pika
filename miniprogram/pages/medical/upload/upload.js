const { BASE_URL } = require('../../../config');
const { request } = require('../../../utils/request');

const PRESET_HOSPITALS = ['北京大学国际医院', '北京协和医院', '北京积水潭医院', '北京大学肿瘤医院'];
const HOSPITAL_OPTIONS = [...PRESET_HOSPITALS, '其他（可输入）'];
const OTHER_INDEX = PRESET_HOSPITALS.length;

// 模糊匹配：解析出的医院名包含某预设项关键词则选中该项，否则归"其他"。
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
    files: [],
    uploading: false,
    step: 'pick', // pick -> edit
    draftId: '',
    reportType: 'unknown',
    reportTypeLabel: '',
    reportDate: '',
    hospital: '',
    hospitalOptions: HOSPITAL_OPTIONS,
    hospitalIndex: OTHER_INDEX,
    hospitalCustom: '',
    metrics: [],
  },

  // 当前生效的医院名：选了预设项用预设名，选"其他"用自定义输入。
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

  chooseImage() {
    wx.chooseMedia({
      count: 9,
      mediaType: ['image'],
      sourceType: ['camera', 'album'],
      success: (res) => {
        const picked = (res.tempFiles || []).map((f, i) => ({
          id: `${Date.now()}-${i}`,
          path: f.tempFilePath,
        }));
        this.setData({ files: picked, step: 'pick', draftId: '', metrics: [] });
      },
    });
  },

  removeImage(e) {
    const id = e.currentTarget.dataset.id;
    const files = this.data.files.filter((f) => f.id !== id);
    this.setData({ files });
  },

  onMetricFieldInput(e) {
    const { idx, field } = e.currentTarget.dataset;
    const value = e.detail.value;
    const metrics = [...this.data.metrics];
    metrics[idx] = { ...metrics[idx], [field]: value };
    this.setData({ metrics });
  },

  onReportTypeInput(e) {
    this.setData({ reportTypeLabel: e.detail.value || '' });
  },

  createDraft() {
    if (!this.data.files.length) return;
    const token = getApp().globalData.token || wx.getStorageSync('token') || '';

    // 没有 token 直接提示(说明登录没成功)
    if (!token) {
      wx.showModal({
        title: '未登录',
        content: '没有拿到登录 token，无法上传。多半是 app.js 自动登录失败（检查后端 /api/auth/login 与微信 AppSecret）。',
        showCancel: false,
      });
      return;
    }

    this.setData({ uploading: true });

    const uploads = this.data.files.map((f) =>
      new Promise((resolve, reject) => {
        wx.uploadFile({
          url: BASE_URL + '/api/medical/report-drafts',
          filePath: f.path,
          name: 'files',
          timeout: 60000,
          formData: {
            hospital: this.resolvedHospital(),
          },
          header: { 'X-Pika-Token': token },
          success: (res) => {
            try {
              const body = JSON.parse(res.data);
              if (body.code === 0) {
                resolve(body.data);
              } else {
                const e = new Error(body.msg || `code=${body.code}`);
                e.bizCode = body.code;
                reject(e);
              }
            } catch (_e) {
              reject(new Error(`HTTP ${res.statusCode}: ${String(res.data).slice(0, 200)}`));
            }
          },
          fail: (e) => reject(new Error('网络错误: ' + (e.errMsg || ''))),
        });
      })
    );

    Promise.all(uploads)
      .then((all) => {
        const first = all[0];
        const enterEdit = () => {
          const matched = matchHospital(first.hospital || this.resolvedHospital());
          this.setData({
            step: 'edit',
            draftId: first.draft_id,
            reportType: first.report_type || 'unknown',
            reportTypeLabel: first.report_type_label || '',
            reportDate: first.report_date || '',
            hospital: first.hospital || this.resolvedHospital(),
            hospitalIndex: matched.index,
            hospitalCustom: matched.custom,
            metrics: first.metrics || [],
          });
        };
        // 软提醒：模型判定不是检查单时，让用户决定是否继续。
        if (first.is_lab_report === false) {
          wx.showModal({
            title: '可能不是检查单',
            content: '这张图看起来不像医学检查单，识别结果可能不准。仍要继续编辑并提交吗？',
            confirmText: '仍要继续',
            cancelText: '返回重选',
            success: (r) => {
              if (r.confirm) enterEdit();
            },
          });
        } else {
          enterEdit();
        }
      })
      .catch((err) => {
        wx.showModal({
          title: err && err.bizCode === 4090 ? '重复上传' : '识别失败',
          content: (err && err.message) || '预解析失败',
          showCancel: false,
        });
      })
      .finally(() => {
        this.setData({ uploading: false });
      });
  },

  submitDraft() {
    if (!this.data.draftId) return;

    const reportTypeLabel = this.data.reportTypeLabel || null;
    const reportType = reportTypeLabel ? 'custom' : this.data.reportType;

    request({
      url: `/api/medical/report-drafts/${this.data.draftId}/commit`,
      method: 'POST',
      data: {
        report_type: reportType,
        report_type_label: reportTypeLabel,
        report_date: this.data.reportDate || null,
        hospital: this.resolvedHospital() || null,
        metrics: this.data.metrics,
      },
    })
      .then((data) => {
        this.setData({
          step: 'pick',
          draftId: '',
          files: [],
          metrics: [],
        });
        wx.showToast({ title: '提交成功', icon: 'success' });
        setTimeout(() => {
          wx.navigateTo({ url: `/pages/medical/report-detail/report-detail?id=${data.report.id}` });
        }, 300);
      })
      .catch(() => {
        wx.showToast({ title: '提交失败', icon: 'none' });
      });
  },
});
