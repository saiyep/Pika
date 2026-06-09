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
    visibleServices: [],
    favoriteKeys: [],
    favoriteServices: [],
  },

  onShow() {
    this.loadFavorites();
  },

  loadFavorites() {
    request({ url: '/api/user/favorites' })
      .then((data) => this.applyFavorites(data.service_keys || []))
      .catch(() => this.applyFavorites(this.data.favoriteKeys));
  },

  applyFavorites(keys) {
    this.setData(
      {
        favoriteKeys: keys,
        favoriteServices: SERVICES.filter((s) => keys.indexOf(s.key) >= 0),
      },
      () => this.applyCategory()
    );
  },

  onCategoryPick(e) {
    const idx = Number(e.currentTarget.dataset.idx);
    this.setData({ categoryIndex: idx }, () => this.applyCategory());
  },

  applyCategory() {
    const cat = this.data.categories[this.data.categoryIndex];
    const keys = this.data.favoriteKeys;
    const list = (cat === '全部' ? SERVICES : SERVICES.filter((s) => s.category === cat)).map(
      (s) => ({ ...s, isFav: keys.indexOf(s.key) >= 0 })
    );
    this.setData({ visibleServices: list });
  },

  openService(e) {
    const path = e.currentTarget.dataset.path;
    if (path) wx.navigateTo({ url: path });
  },

  toggleFavorite(e) {
    const key = e.currentTarget.dataset.key;
    const isFav = this.data.favoriteKeys.indexOf(key) >= 0;
    const req = isFav
      ? request({ url: `/api/user/favorites/${key}`, method: 'DELETE' })
      : request({ url: '/api/user/favorites', method: 'POST', data: { service_key: key } });
    req
      .then((data) => {
        this.applyFavorites(data.service_keys || []);
        wx.showToast({ title: isFav ? '已取消关注' : '已关注', icon: 'none' });
      })
      .catch(() => {
        wx.showToast({ title: '操作失败', icon: 'none' });
      });
  },
});
