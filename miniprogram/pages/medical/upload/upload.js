const { BASE_URL } = require('../../../config');
const { request } = require('../../../utils/request');

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
    metrics: [],
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

  onHospitalInput(e) {
    this.setData({ hospital: e.detail.value || '' });
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
    this.setData({ uploading: true });

    const uploads = this.data.files.map((f) =>
      new Promise((resolve, reject) => {
        wx.uploadFile({
          url: BASE_URL + '/api/medical/report-drafts',
          filePath: f.path,
          name: 'files',
          formData: {
            hospital: this.data.hospital,
          },
          header: { 'X-Pika-Token': token },
          success: (res) => {
            try {
              const body = JSON.parse(res.data);
              if (body.code === 0) {
                resolve(body.data);
              } else {
                reject(new Error(body.msg || '上传失败'));
              }
            } catch (_e) {
              reject(new Error('返回解析失败'));
            }
          },
          fail: () => reject(new Error('网络错误')),
        });
      })
    );

    Promise.all(uploads)
      .then((all) => {
        const first = all[0];
        this.setData({
          step: 'edit',
          draftId: first.draft_id,
          reportType: first.report_type || 'unknown',
          reportTypeLabel: first.report_type_label || '',
          reportDate: first.report_date || '',
          hospital: first.hospital || this.data.hospital,
          metrics: first.metrics || [],
        });
      })
      .catch((err) => {
        wx.showToast({ title: err.message || '预解析失败', icon: 'none' });
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
        hospital: this.data.hospital || null,
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
