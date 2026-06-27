const { request } = require('../../../utils/request');

const PALETTE = ['#07c160', '#4b8bf4', '#fa8c16', '#a64dff', '#13c2c2'];

Page({
  data: {
    members: [],
    memberLabels: [],
    selectedMemberIndex: 0,
    selectedMemberId: null,
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
        this.setData(
          {
            members,
            memberLabels: members.map((m) => m.nickname || ('用户' + m.id)),
            selectedMemberIndex: idx >= 0 ? idx : 0,
            selectedMemberId: selectedMember ? selectedMember.id : null,
            membersLoading: false,
          },
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
    this.setData({
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
    }, () => {
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

  onChartTap(e) {
    if (!this.chartHitAreas || !this.chartHitAreas.length) return;
    const { x, y } = e.detail || {};
    if (typeof x !== 'number' || typeof y !== 'number') return;

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

  loadCatalog() {
    if (!this.data.selectedMemberId) return;
    this.setData({ catalogLoading: true, trendLoading: false });
    request({ url: `/api/medical/metrics/catalog?subject_id=${this.data.selectedMemberId}` })
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
    request({ url: `/api/medical/metrics/trend?${q}&subject_id=${this.data.selectedMemberId}` })
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
        ctx.font = '16px sans-serif';
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
        ctx.font = '16px sans-serif';
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
