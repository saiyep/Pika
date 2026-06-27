const { BASE_URL } = require('../../../config');
const { request } = require('../../../utils/request');


Page({
  withRetries(taskFn, options = {}) {
    const maxRetries = options.maxRetries == null ? 2 : options.maxRetries;
    const shouldRetry = options.shouldRetry || (() => false);
    const onRetry = options.onRetry || (() => {});

    const run = (attempt) => taskFn().catch((err) => {
      if (attempt <= maxRetries && shouldRetry(err)) {
        onRetry(attempt, err);
        return run(attempt + 1);
      }
      throw err;
    });

    return run(1);
  },

  isTransientErr(err) {
    const msg = String((err && (err.message || err.errMsg || err.msg)) || '').toLowerCase();
    if (!msg) return false;
    return msg.includes('network')
      || msg.includes('timeout')
      || msg.includes('reset')
      || msg.includes('request:fail')
      || msg.includes('connect')
      || msg.includes('http 5');
  },

  data: {
    files: [],
    uploading: false,
    uploadRetrying: false,
    uploadProgress: 0,
    uploadStageText: '',
    committing: false,
    commitRetrying: false,
    step: 'pick', // pick -> edit
    draftId: '',
    reportType: 'unknown',
    reportTypeLabel: '',
    reportDate: '',
    hospital: '',
    metrics: [],
    // 被检查人（报告属于谁）
    members: [],
    memberLabels: [],
    subjectIndex: 0,
  },

  onShow() {
    this.loadMembers();
  },

  loadMembers() {
    request({ url: '/api/user/members' })
      .then((data) => {
        const members = (data.items || []).filter((m) => m.status !== 'disabled');
        const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
        let idx = members.findIndex((m) => m.id === myId);
        if (idx < 0) idx = 0;
        this.setData({
          members,
          memberLabels: members.map((m) => m.nickname || ('用户' + m.id)),
          subjectIndex: idx,
        });
      })
      .catch(() => {
        // 成员拉取失败不阻断上传，subject 留空即可。
      });
  },

  onSubjectPick(e) {
    this.setData({ subjectIndex: Number(e.detail.value) });
  },

  subjectId() {
    const m = this.data.members[this.data.subjectIndex];
    return m ? m.id : '';
  },

  resolvedHospital() {
    return (this.data.hospital || '').trim();
  },

  onHospitalInput(e) {
    this.setData({ hospital: e.detail.value || '' });
  },

  onReportDateInput(e) {
    this.setData({ reportDate: e.detail.value || '' });
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
        this.setData({
          files: picked,
          step: 'pick',
          draftId: '',
          metrics: [],
          reportType: 'unknown',
          reportTypeLabel: '',
          reportDate: '',
          hospital: '',
        });
        wx.setNavigationBarTitle({ title: '上传检查单' });
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
    if (!this.data.files.length || this.data.uploading) return;
    const token = getApp().globalData.token || wx.getStorageSync('token') || '';

    if (!token) {
      wx.showModal({
        title: '未登录',
        content: '没有拿到登录 token，无法上传。多半是自动登录失败，请先回“我”页登录。',
        showCancel: false,
      });
      return;
    }

    let progressTimer = null;
    const startProgress = () => {
      this.setData({
        uploading: true,
        uploadRetrying: false,
        uploadProgress: 8,
        uploadStageText: '正在上传图片并识别检查项，请稍候…',
      });
      progressTimer = setInterval(() => {
        const next = Math.min(90, (this.data.uploadProgress || 0) + 6);
        this.setData({ uploadProgress: next });
      }, 800);
    };
    const stopProgress = () => {
      if (progressTimer) clearInterval(progressTimer);
      progressTimer = null;
    };

    startProgress();

    const parseOnce = () => {
      const uploads = this.data.files.map((f) =>
        new Promise((resolve, reject) => {
          wx.uploadFile({
            url: BASE_URL + '/api/medical/report-drafts',
            filePath: f.path,
            name: 'files',
            timeout: 60000,
            formData: {
              subject_id: this.subjectId(),
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
      return Promise.all(uploads);
    };

    this.withRetries(parseOnce, {
      maxRetries: 2,
      shouldRetry: (err) => this.isTransientErr(err) && !(err && err.bizCode),
      onRetry: () => this.setData({
        uploadRetrying: true,
        uploadStageText: '网络波动，正在重试识别…',
      }),
    })
      .then((all) => {
        this.setData({ uploadProgress: 100, uploadStageText: '识别完成，正在整理结果…' });
        const first = all[0];
        const enterEdit = () => {
          this.setData({
            step: 'edit',
            draftId: first.draft_id,
            reportType: first.report_type || 'unknown',
            reportTypeLabel: first.report_type_label || '',
            reportDate: first.report_date || '',
            hospital: first.hospital || '',
            metrics: first.metrics || [],
          });
          wx.setNavigationBarTitle({ title: '确认检查信息' });
        };
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
        stopProgress();
        this.setData({
          uploading: false,
          uploadRetrying: false,
          uploadProgress: 0,
          uploadStageText: '',
        });
      });
  },

  submitDraft() {
    if (!this.data.draftId || this.data.committing) return;

    const subjectId = this.subjectId();
    const hospital = this.resolvedHospital();
    const reportTypeLabel = (this.data.reportTypeLabel || '').trim();
    const reportDate = (this.data.reportDate || '').trim();

    if (!subjectId) {
      wx.showToast({ title: '请选择被检查人', icon: 'none' });
      return;
    }
    if (!hospital) {
      wx.showToast({ title: '请填写医院', icon: 'none' });
      return;
    }
    if (!reportTypeLabel) {
      wx.showToast({ title: '请填写报告类型', icon: 'none' });
      return;
    }
    if (!reportDate) {
      wx.showToast({ title: '请填写报告日期', icon: 'none' });
      return;
    }

    const reportType = 'custom';

    this.setData({ committing: true, commitRetrying: false });

    const commitOnce = () => request({
      url: `/api/medical/report-drafts/${this.data.draftId}/commit`,
      method: 'POST',
      data: {
        report_type: reportType,
        report_type_label: reportTypeLabel,
        report_date: reportDate,
        hospital,
        metrics: this.data.metrics,
      },
    });

    this.withRetries(commitOnce, {
      maxRetries: 2,
      shouldRetry: (err) => this.isTransientErr(err) && !(err && err.code),
      onRetry: () => this.setData({ commitRetrying: true }),
    })
      .then(() => {
        this.setData({
          step: 'pick',
          draftId: '',
          files: [],
          metrics: [],
          reportType: 'unknown',
          reportTypeLabel: '',
          reportDate: '',
          hospital: '',
        });
        wx.setNavigationBarTitle({ title: '上传检查单' });
        wx.showToast({ title: '保存成功', icon: 'success' });
        setTimeout(() => {
          wx.redirectTo({ url: '/pages/medical/history/history' });
        }, 300);
      })
      .catch(() => {
        wx.showToast({ title: '提交失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ committing: false, commitRetrying: false });
      });
  },
});
