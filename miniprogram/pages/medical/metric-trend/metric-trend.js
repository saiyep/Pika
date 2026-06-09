const { request } = require('../../../utils/request');

Page({
  data: {
    catalog: [],
    catalogLabels: [],
    selectedIndex: 0,
    trend: null,
    // 被检查人 filter
    members: [],
    filterLabels: ['全家'],
    filterIndex: 0,
  },

  onLoad() {
    this.loadMembers();
  },

  loadMembers() {
    request({ url: '/api/user/members' })
      .then((data) => {
        const members = data.items || [];
        const myId = (getApp().globalData.user && getApp().globalData.user.id) || null;
        let idx = members.findIndex((m) => m.id === myId);
        idx = idx < 0 ? 0 : idx + 1;
        this.setData(
          {
            members,
            filterLabels: ['全家', ...members.map((m) => m.nickname || ('用户' + m.id))],
            filterIndex: idx,
          },
          () => this.loadCatalog()
        );
      })
      .catch(() => {
        this.loadCatalog();
      });
  },

  subjectQuery() {
    if (this.data.filterIndex > 0) {
      const m = this.data.members[this.data.filterIndex - 1];
      if (m) return '&subject_id=' + m.id;
    }
    return '';
  },

  onFilterPick(e) {
    this.setData({ filterIndex: Number(e.detail.value), selectedIndex: 0 }, () => this.loadCatalog());
  },

  loadCatalog() {
    request({ url: '/api/medical/metrics/catalog?_=1' + this.subjectQuery() })
      .then((data) => {
        const catalog = data.items || [];
        this.setData({
          catalog,
          catalogLabels: catalog.map((c) => `${c.item_name} (${c.count})`),
        });
        if (catalog.length) {
          this.loadTrend(catalog[0]);
        } else {
          this.setData({ trend: null });
          wx.nextTick(() => this.draw({ points: [] }));
        }
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },

  onPick(e) {
    const idx = Number(e.detail.value);
    this.setData({ selectedIndex: idx });
    this.loadTrend(this.data.catalog[idx]);
  },

  loadTrend(item) {
    const q = item.item_code
      ? 'item_code=' + encodeURIComponent(item.item_code)
      : 'item_name=' + encodeURIComponent(item.item_name);
    request({ url: '/api/medical/metrics/trend?' + q + this.subjectQuery() })
      .then((trend) => {
        this.setData({ trend });
        wx.nextTick(() => this.draw(trend));
      })
      .catch(() => {
        wx.showToast({ title: '加载趋势失败', icon: 'none' });
      });
  },

  draw(trend) {
    const points = (trend.points || []).filter((p) => p.value_num !== null);
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

        if (points.length === 0) return;

        const pad = { l: 48, r: 16, t: 16, b: 28 };
        const plotW = W - pad.l - pad.r;
        const plotH = H - pad.t - pad.b;

        const values = points.map((p) => p.value_num);
        let vmin = Math.min(...values, trend.ref_low != null ? trend.ref_low : Infinity);
        let vmax = Math.max(...values, trend.ref_high != null ? trend.ref_high : -Infinity);
        if (!isFinite(vmin)) vmin = Math.min(...values);
        if (!isFinite(vmax)) vmax = Math.max(...values);
        if (vmin === vmax) { vmin -= 1; vmax += 1; }
        const span = vmax - vmin;
        vmin -= span * 0.1;
        vmax += span * 0.1;

        const xAt = (i) =>
          pad.l + (points.length === 1 ? plotW / 2 : (plotW * i) / (points.length - 1));
        const yAt = (v) => pad.t + plotH - (plotH * (v - vmin)) / (vmax - vmin);

        // reference band
        if (trend.ref_low != null && trend.ref_high != null) {
          ctx.fillStyle = 'rgba(7,193,96,0.12)';
          const yHigh = yAt(trend.ref_high);
          const yLow = yAt(trend.ref_low);
          ctx.fillRect(pad.l, yHigh, plotW, yLow - yHigh);
        }

        // axes
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad.l, pad.t);
        ctx.lineTo(pad.l, pad.t + plotH);
        ctx.lineTo(pad.l + plotW, pad.t + plotH);
        ctx.stroke();

        // y labels (min/max)
        ctx.fillStyle = '#999';
        ctx.font = '20px sans-serif';
        ctx.fillText(vmax.toFixed(1), 4, pad.t + 8);
        ctx.fillText(vmin.toFixed(1), 4, pad.t + plotH);

        // line
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

        // points (color by hospital)
        const colorByHospital = {};
        const palette = ['#07c160', '#4b8bf4', '#fa8c16', '#a64dff', '#13c2c2'];
        let colorIdx = 0;

        points.forEach((p, i) => {
          const x = xAt(i);
          const y = yAt(p.value_num);
          const key = p.hospital || 'unknown';
          if (!colorByHospital[key]) {
            colorByHospital[key] = palette[colorIdx % palette.length];
            colorIdx += 1;
          }
          ctx.fillStyle = colorByHospital[key];
          ctx.beginPath();
          ctx.arc(x, y, 4, 0, Math.PI * 2);
          ctx.fill();
        });
      });
  },
});
