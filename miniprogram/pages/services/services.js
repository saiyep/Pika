const { request } = require('../../utils/request');

// 服务定义（前端写死）。将来加服务在这里扩展。
const SERVICES = [
  { key: 'medical', name: '就医服务', icon: '🏥', category: '健康', path: '/pages/medical/home/home' },
];
const CATEGORIES = ['全部', ...Array.from(new Set(SERVICES.map((s) => s.category)))];

Page({
  data: {
    categories: CATEGORIES,
    categoryIndex: 0,
    services: SERVICES,
    visibleServices: SERVICES,
    favoriteKeys: [],
    favoriteServices: [],
  },

  onShow() {
    this.applyCategory();
    this.loadFavorites();
  },

  loadFavorites() {
    request({ url: '/api/medical/favorites' })
      .then((data) => {
        const keys = data.service_keys || [];
        this.setData({
          favoriteKeys: keys,
          favoriteServices: SERVICES.filter((s) => keys.indexOf(s.key) >= 0),
        });
      })
      .catch(() => {});
  },

  onCategoryPick(e) {
    const idx = Number(e.currentTarget.dataset.idx);
    this.setData({ categoryIndex: idx }, () => this.applyCategory());
  },

  applyCategory() {
    const cat = this.data.categories[this.data.categoryIndex];
    const visible = cat === '全部' ? SERVICES : SERVICES.filter((s) => s.category === cat);
    this.setData({ visibleServices: visible });
  },

  openService(e) {
    const path = e.currentTarget.dataset.path;
    if (path) wx.navigateTo({ url: path });
  },

  toggleFavorite(e) {
    const key = e.currentTarget.dataset.key;
    const isFav = this.data.favoriteKeys.indexOf(key) >= 0;
    const req = isFav
      ? request({ url: `/api/medical/favorites/${key}`, method: 'DELETE' })
      : request({ url: '/api/medical/favorites', method: 'POST', data: { service_key: key } });
    req
      .then((data) => {
        const keys = data.service_keys || [];
        this.setData({
          favoriteKeys: keys,
          favoriteServices: SERVICES.filter((s) => keys.indexOf(s.key) >= 0),
        });
        wx.showToast({ title: isFav ? '已取消关注' : '已关注', icon: 'none' });
      })
      .catch(() => {
        wx.showToast({ title: '操作失败', icon: 'none' });
      });
  },
});
