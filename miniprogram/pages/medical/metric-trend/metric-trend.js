const { request } = require('../../../utils/request');

const PALETTE = ['#07c160', '#4b8bf4', '#fa8c16', '#a64dff', '#13c2c2'];
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
    members: [],
    memberLabels: [],
    selectedMemberIndex: 0,
    selectedMemberId: null,
    memberDisplay: '选择成员',
    membersLoading: true,
    catalogLoading: false,
    trendLoading: false,
    catalog: [],
    catalogLabels: [],
    selectedIndex: 0,
    trend: null,
    tableRows: [],
    chartPointsCount: 0,
    viewMode: 'table',
    activeTooltip: null,
    timeRanges: TIME_RANGES,
    timeIndex: DEFAULT_TIME_INDEX,
    timeDisplay: TIME_RANGES[DEFAULT_TIME_INDEX],
    customFrom: '',
    customTo: '',
    showCustom: false,
  },

  formatMemberDisplay(memberLabels, selectedMemberIndex) {
    return memberLabels.length ? (memberLabels[selectedMemberIndex] || '选择成员') : '选择成员';
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

  refreshDisplay(partial = {}) {
    const memberLabels = partial.memberLabels || this.data.memberLabels;
    const selectedMemberIndex = partial.selectedMemberIndex !== undefined ? partial.selectedMemberIndex : this.data.selectedMemberIndex;
    const timeRanges = partial.timeRanges || this.data.timeRanges;
    const timeIndex = partial.timeIndex !== undefined ? partial.timeIndex : this.data.timeIndex;
    const customFrom = partial.customFrom !== undefined ? partial.customFrom : this.data.customFrom;
    const customTo = partial.customTo !== undefined ? partial.customTo : this.data.customTo;
    return {
      memberDisplay: this.formatMemberDisplay(memberLabels, selectedMemberIndex),
      timeDisplay: this.formatTimeDisplay(timeIndex, customFrom, customTo, timeRanges),
    };
  },

  currentDateRange() {
    const ti = this.data.timeIndex;
    if (ti >= 0 && ti <= 3) {
      const map = { 0: 1, 1: 3, 2: 6, 3: 12 };
      return { date_from: monthsAgo(map[ti]), date_to: '' };
    }
    if (ti === CUSTOM_INDEX) {
      return { date_from: this.data.customFrom || '', date_to: this.data.customTo || '' };
    }
    return { date_from: '', date_to: '' };
  },

  onTimePick(e) {
    const idx = Number(e.detail.value);
    const next = { timeIndex: idx, showCustom: idx === CUSTOM_INDEX };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.loadCatalog());
  },

  onCustomFrom(e) {
    const next = { customFrom: e.detail.value };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.loadCatalog());
  },

  onCustomTo(e) {
    const next = { customTo: e.detail.value };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => this.loadCatalog());
  },

  catalogQuery() {
    const range = this.currentDateRange();
    const parts = [];
    if (range.date_from) parts.push('date_from=' + encodeURIComponent(range.date_from));
    if (range.date_to) parts.push('date_to=' + encodeURIComponent(range.date_to));
    return parts.length ? '&' + parts.join('&') : '';
  },


  onLoad() {
    this.chartHitAreas = [];
    this.loadMembers();
  },

  loadMembers() {
    this.setData({ membersLoading: true });
    request({ url: '/api/user/members' })
      .then((data) => {
        const members = data.items || [];
        const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
        let idx = members.findIndex((m) => m.id === myId);
        if (idx < 0) idx = members.length ? 0 : -1;
        const selectedMember = idx >= 0 ? members[idx] : null;
        const memberLabels = members.map((m) => m.nickname || ('用户' + m.id));
        const next = {
          members,
          memberLabels,
          selectedMemberIndex: idx >= 0 ? idx : 0,
          selectedMemberId: selectedMember ? selectedMember.id : null,
          membersLoading: false,
        };
        this.setData(
          { ...next, ...this.refreshDisplay(next) },
          () => {
            if (selectedMember) this.loadCatalog();
          }
        );
      })
      .catch(() => {
        this.setData({ membersLoading: false, members: [], memberLabels: [], selectedMemberId: null });
      });
  },

  selectedMember() {
    return this.data.members[this.data.selectedMemberIndex] || null;
  },

  onMemberPick(e) {
    const idx = Number(e.detail.value);
    const member = this.data.members[idx] || null;
    this.chartHitAreas = [];
    const next = {
      selectedMemberIndex: idx,
      selectedMemberId: member ? member.id : null,
      selectedIndex: 0,
      catalog: [],
      catalogLabels: [],
      trend: null,
      tableRows: [],
      chartPointsCount: 0,
      viewMode: 'table',
      activeTooltip: null,
    };
    this.setData({ ...next, ...this.refreshDisplay(next) }, () => {
      if (member) this.loadCatalog();
    });
  },

  onSwitchView(e) {
    const mode = e.currentTarget.dataset.mode;
    if (!mode || mode === this.data.viewMode) return;
    this.setData({ viewMode: mode, activeTooltip: null }, () => {
      if (mode === 'chart') wx.nextTick(() => this.draw(this.data.trend || { points: [] }));
    });
  },

  onTableRowTap(e) {
    const reportId = e.currentTarget.dataset.reportId;
    if (!reportId) return;
    wx.navigateTo({ url: '/pages/medical/report-detail/report-detail?id=' + reportId });
  },

  onChartTouch(e) {
    if (!this.chartHitAreas || !this.chartHitAreas.length) return;
    const touch = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0]) || null;
    if (!touch) return;
    const x = typeof touch.x === 'number' ? touch.x : typeof touch.clientX === 'number' ? touch.clientX : null;
    const y = typeof touch.y === 'number' ? touch.y : typeof touch.clientY === 'number' ? touch.clientY : null;
    if (x === null || y === null) return;

    let hit = null;
    let minDistance = Infinity;
    this.chartHitAreas.forEach((point) => {
      const dx = point.x - x;
      const dy = point.y - y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance <= point.hitRadius && distance < minDistance) {
        hit = point;
        minDistance = distance;
      }
    });

    if (!hit) {
      this.setData({ activeTooltip: null });
      return;
    }

    this.setData({
      activeTooltip: {
        ...hit.row,
        left: Math.max(74, Math.min(hit.x, hit.chartWidth - 74)),
        top: Math.max(54, hit.y),
      },
    });
  },

  onChartTap(e) {
    this.onChartTouch(e);
  },

  loadCatalog() {
    if (!this.data.selectedMemberId) return;
    this.setData({ catalogLoading: true, trendLoading: false });
    request({ url: `/api/medical/metrics/catalog?subject_id=${this.data.selectedMemberId}${this.catalogQuery()}` })
      .then((data) => {
        const catalog = data.items || [];
        this.setData({
          catalog,
          catalogLabels: catalog.map((c) => `${c.item_name} (${c.count})`),
          selectedIndex: 0,
          catalogLoading: false,
        });
        if (catalog.length) {
          this.loadTrend(catalog[0], { resetView: true });
        } else {
          this.chartHitAreas = [];
          this.setData({ trend: null, tableRows: [], chartPointsCount: 0, activeTooltip: null });
        }
      })
      .catch((err) => {
        this.chartHitAreas = [];
        this.setData({ catalogLoading: false, catalog: [], catalogLabels: [], trend: null, tableRows: [], chartPointsCount: 0, activeTooltip: null });
        if (!(err && err.code === 403)) {
          wx.showToast({ title: '加载指标失败', icon: 'none' });
        }
      });
  },

  onPick(e) {
    const idx = Number(e.detail.value);
    this.setData({ selectedIndex: idx, activeTooltip: null });
    this.loadTrend(this.data.catalog[idx], { resetView: false });
  },

  loadTrend(item, { resetView }) {
    if (!item || !this.data.selectedMemberId) return;
    const q = item.item_code
      ? 'item_code=' + encodeURIComponent(item.item_code)
      : 'item_name=' + encodeURIComponent(item.item_name);
    this.setData({ trendLoading: true, activeTooltip: null });
    const range = this.currentDateRange();
    const extra = [];
    if (range.date_from) extra.push('date_from=' + encodeURIComponent(range.date_from));
    if (range.date_to) extra.push('date_to=' + encodeURIComponent(range.date_to));
    request({ url: `/api/medical/metrics/trend?${q}&subject_id=${this.data.selectedMemberId}${extra.length ? '&' + extra.join('&') : ''}` })
      .then((trend) => {
        this.setTrendData(trend, { resetView });
        if ((resetView ? 'table' : this.data.viewMode) === 'chart') {
          wx.nextTick(() => this.draw(trend));
        }
      })
      .catch((err) => {
        this.chartHitAreas = [];
        this.setData({ trendLoading: false, trend: null, tableRows: [], chartPointsCount: 0, activeTooltip: null });
        if (!(err && err.code === 403)) {
          wx.showToast({ title: '加载趋势失败', icon: 'none' });
        }
      });
  },

  setTrendData(trend, { resetView }) {
    if (!trend) {
      this.chartHitAreas = [];
      this.setData({ trend: null, tableRows: [], chartPointsCount: 0, activeTooltip: null, trendLoading: false });
      return;
    }
    const chartRows = (trend.points || []).filter((p) => p.value_num !== null);
    const tableRows = (trend.points || []).map((p) => this.formatRow(p, trend.unit));
    this.chartHitAreas = [];
    this.setData({
      trend,
      tableRows,
      chartPointsCount: chartRows.length,
      viewMode: resetView ? 'table' : this.data.viewMode,
      activeTooltip: null,
      trendLoading: false,
    });
  },

  formatRow(point, defaultUnit) {
    const unit = point.unit || defaultUnit || '';
    const valueText = point.value_text != null && point.value_text !== ''
      ? point.value_text
      : (point.value_num != null ? String(point.value_num) : '—');
    return {
      ...point,
      displayDate: point.report_date || '日期未知',
      displayHospital: point.hospital || '医院未知',
      displayValue: valueText === '—' ? '—' : `${valueText}${unit ? ' ' + unit : ''}`,
      displayRef: point.ref_range || '—',
    };
  },

  buildHospitalColors(points) {
    const colorByHospital = {};
    let colorIdx = 0;
    points.forEach((p) => {
      const key = p.hospital || 'unknown';
      if (!colorByHospital[key]) {
        colorByHospital[key] = PALETTE[colorIdx % PALETTE.length];
        colorIdx += 1;
      }
    });
    return colorByHospital;
  },

  getNiceStep(rawStep) {
    if (!isFinite(rawStep) || rawStep <= 0) return 1;
    const exponent = Math.floor(Math.log10(rawStep));
    const fraction = rawStep / Math.pow(10, exponent);
    let niceFraction = 1;
    if (fraction <= 1) niceFraction = 1;
    else if (fraction <= 2) niceFraction = 2;
    else if (fraction <= 2.5) niceFraction = 2.5;
    else if (fraction <= 5) niceFraction = 5;
    else niceFraction = 10;
    return niceFraction * Math.pow(10, exponent);
  },

  buildTicks(vmin, vmax, count = 5) {
    const span = vmax - vmin;
    const step = this.getNiceStep(span / Math.max(count - 1, 1));
    const niceMin = Math.floor(vmin / step) * step;
    const niceMax = Math.ceil(vmax / step) * step;
    const ticks = [];
    for (let value = niceMin; value <= niceMax + step * 0.5; value += step) {
      ticks.push(Number(value.toFixed(6)));
    }
    return { ticks, min: niceMin, max: niceMax, step };
  },

  formatTick(value, step) {
    if (!isFinite(value)) return '';
    if (step >= 10) return String(Math.round(value));
    if (step >= 1) return value.toFixed(1).replace(/\.0$/, '');
    if (step >= 0.1) return value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
    return value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  },

  getXLabelIndices(length) {
    if (length <= 1) return [0];
    if (length === 2) return [0, 1];
    return [0, Math.floor((length - 1) / 2), length - 1];
  },

  isAbnormal(point) {
    return point.abnormal_flag === 'high' || point.abnormal_flag === 'low';
  },

  draw(trend) {
    const points = (trend.points || []).filter((p) => p.value_num !== null);
    const formattedRows = points.map((p) => this.formatRow(p, trend.unit));
    const query = wx.createSelectorQuery();
    query
      .select('#trendCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res[0] || !res[0].node) return;
        const canvas = res[0].node;
        const ctx = canvas.getContext('2d');
        const dpr = wx.getSystemInfoSync().pixelRatio;
        const W = res[0].width;
        const H = res[0].height;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, W, H);
        this.chartHitAreas = [];

        if (points.length === 0) return;

        const pad = { l: 56, r: 18, t: 18, b: 56 };
        const plotW = W - pad.l - pad.r;
        const plotH = H - pad.t - pad.b;

        const values = points.map((p) => p.value_num);
        if (trend.ref_low != null) values.push(trend.ref_low);
        if (trend.ref_high != null) values.push(trend.ref_high);
        let vmin = Math.min(...values);
        let vmax = Math.max(...values);
        if (vmin === vmax) { vmin -= 1; vmax += 1; }
        const span = vmax - vmin;
        vmin -= span * 0.1;
        vmax += span * 0.1;

        const scale = this.buildTicks(vmin, vmax, 6);
        const xAt = (i) => pad.l + (points.length === 1 ? plotW / 2 : (plotW * i) / (points.length - 1));
        const yAt = (v) => pad.t + plotH - (plotH * (v - scale.min)) / (scale.max - scale.min);
        const colorByHospital = this.buildHospitalColors(points);

        if (trend.ref_low != null && trend.ref_high != null) {
          ctx.fillStyle = 'rgba(7,193,96,0.12)';
          const yHigh = yAt(trend.ref_high);
          const yLow = yAt(trend.ref_low);
          ctx.fillRect(pad.l, yHigh, plotW, yLow - yHigh);
        }

        ctx.strokeStyle = '#f0f0f0';
        ctx.lineWidth = 1;
        scale.ticks.forEach((tick) => {
          const y = yAt(tick);
          ctx.beginPath();
          ctx.moveTo(pad.l, y);
          ctx.lineTo(pad.l + plotW, y);
          ctx.stroke();
        });

        ctx.strokeStyle = '#d9d9d9';
        ctx.beginPath();
        ctx.moveTo(pad.l, pad.t);
        ctx.lineTo(pad.l, pad.t + plotH);
        ctx.lineTo(pad.l + plotW, pad.t + plotH);
        ctx.stroke();

        ctx.fillStyle = '#999';
        ctx.font = '14px sans-serif';
        scale.ticks.forEach((tick) => {
          const y = yAt(tick);
          ctx.fillText(this.formatTick(tick, scale.step), 4, y + 5);
        });

        ctx.strokeStyle = '#07c160';
        ctx.lineWidth = 2;
        ctx.beginPath();
        points.forEach((p, i) => {
          const x = xAt(i);
          const y = yAt(p.value_num);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();

        points.forEach((p, i) => {
          const x = xAt(i);
          const y = yAt(p.value_num);
          const key = p.hospital || 'unknown';
          const radius = 4;
          const row = formattedRows[i];

          if (this.isAbnormal(p)) {
            ctx.strokeStyle = '#e64340';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(x, y, radius + 3, 0, Math.PI * 2);
            ctx.stroke();
          }

          ctx.fillStyle = colorByHospital[key];
          ctx.beginPath();
          ctx.arc(x, y, radius, 0, Math.PI * 2);
          ctx.fill();

          this.chartHitAreas.push({ x, y, row, hitRadius: 18, chartWidth: W });
        });

        const labelIndexes = this.getXLabelIndices(points.length);
        ctx.fillStyle = '#999';
        ctx.font = '14px sans-serif';
        labelIndexes.forEach((idx) => {
          const point = points[idx];
          if (!point) return;
          const x = xAt(idx);
          const label = point.report_date || '未知';
          const metrics = ctx.measureText(label);
          ctx.fillText(label, x - metrics.width / 2, H - 12);
        });
      });
  },
});
