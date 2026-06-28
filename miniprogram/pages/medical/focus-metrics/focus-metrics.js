const { request } = require('../../../utils/request');

Page({
  data: {
    items: [],
    categories: [],
    catalog: [],
  },

  onShow() {
    this.loadAll();
  },

  loadAll() {
    Promise.all([
      request({ url: '/api/medical/focus-metrics' }),
      request({ url: '/api/medical/categories' }),
      request({ url: '/api/medical/metrics/catalog?mapped=1' }),
    ])
      .then(([focusData, categoryData, catalogData]) => {
        this.setData({
          items: focusData.items || [],
          categories: categoryData.items || [],
          catalog: catalogData.items || [],
        });
      })
      .catch(() => wx.showToast({ title: '加载失败', icon: 'none' }));
  },

  goMappingSettings() {
    wx.navigateTo({ url: '/pages/medical/mapping-settings/mapping-settings' });
  },

  pickCategoryAndRun(confirmText, onConfirm) {
    const categories = this.data.categories || [];
    if (categories.length === 0) {
      wx.showToast({ title: '请先新增检查单分类', icon: 'none' });
      return;
    }
    wx.showActionSheet({
      itemList: categories.map((c) => c.display_name),
      success: (res) => {
        const category = categories[res.tapIndex];
        wx.showModal({
          title: '确认',
          content: `${confirmText}到“${category.display_name}”？`,
          success: (r) => {
            if (!r.confirm) return;
            onConfirm(category);
          },
        });
      },
    });
  },

  tryRecoverMappedCatalog() {
    return request({ url: '/api/medical/mappings/bootstrap', method: 'POST' })
      .then(() => request({ url: '/api/medical/mappings/rebuild', method: 'POST' }))
      .then(() => request({ url: '/api/medical/metrics/catalog?mapped=1' }))
      .then((data) => {
        const catalog = data.items || [];
        this.setData({ catalog });
        return catalog;
      });
  },

  onAdd() {
    const openPicker = (catalog) => {
      wx.showActionSheet({
        itemList: catalog.map((x) => x.item_name),
        success: (res) => {
          const metric = catalog[res.tapIndex];
          this.pickCategoryAndRun('添加指标', (category) => {
            request({
              url: '/api/medical/focus-metrics',
              method: 'POST',
              data: {
                dictionary_id: metric.dictionary_id,
                category_id: category.id,
              },
            })
              .then((data) => this.setData({ items: data.items || [] }))
              .catch(() => wx.showToast({ title: '添加失败', icon: 'none' }));
          });
        },
      });
    };

    const catalog = this.data.catalog || [];
    if (catalog.length > 0) {
      openPicker(catalog);
      return;
    }

    wx.showLoading({ title: '准备指标中' });
    this.tryRecoverMappedCatalog()
      .then((recovered) => {
        wx.hideLoading();
        if (!recovered || recovered.length === 0) {
          wx.showToast({ title: '暂无可映射指标，请先上传检查单', icon: 'none' });
          return;
        }
        openPicker(recovered);
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: '指标准备失败，请稍后重试', icon: 'none' });
      });
  },

  onEdit(e) {
    const id = Number(e.currentTarget.dataset.id);
    this.pickCategoryAndRun('修改指标分类', (category) => {
      request({
        url: `/api/medical/focus-metrics/${id}`,
        method: 'PATCH',
        data: { category_id: category.id },
      })
        .then((data) => this.setData({ items: data.items || [] }))
        .catch(() => wx.showToast({ title: '修改失败', icon: 'none' }));
    });
  },

  onDelete(e) {
    const id = Number(e.currentTarget.dataset.id);
    request({ url: `/api/medical/focus-metrics/${id}`, method: 'DELETE' })
      .then((data) => this.setData({ items: data.items || [] }))
      .catch(() => wx.showToast({ title: '删除失败', icon: 'none' }));
  },

});
