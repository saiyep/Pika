const { request } = require('../../../utils/request');

Page({
  data: {
    hospitals: [],
    selectedHospital: '',
    aliases: [],
    categories: [],
    catalog: [],
  },

  onShow() {
    this.loadAll();
  },

  loadAll() {
    Promise.all([
      request({ url: '/api/medical/hospitals' }),
      request({ url: '/api/medical/categories' }),
      request({ url: '/api/medical/metrics/catalog?mapped=1' }),
    ])
      .then(([hospitals, categoryData, catalogData]) => {
        this.setData({
          hospitals: hospitals || [],
          categories: categoryData.items || [],
          catalog: catalogData.items || [],
        });
        this.loadAliases();
      })
      .catch(() => wx.showToast({ title: '加载失败', icon: 'none' }));
  },

  loadAliases() {
    const hospitalHint = this.data.selectedHospital;
    const query = hospitalHint ? `?hospital_hint=${encodeURIComponent(hospitalHint)}` : '';
    request({ url: `/api/medical/mappings/aliases${query}` })
      .then((data) => this.setData({ aliases: data.items || [] }))
      .catch(() => wx.showToast({ title: '加载映射失败', icon: 'none' }));
  },

  onPickHospital() {
    const hospitals = this.data.hospitals || [];
    wx.showActionSheet({
      itemList: ['全部医院', ...hospitals],
      success: (res) => {
        const selectedHospital = res.tapIndex === 0 ? '' : hospitals[res.tapIndex - 1];
        this.setData({ selectedHospital }, () => this.loadAliases());
      },
    });
  },

  onAddAlias() {
    const catalog = this.data.catalog || [];
    if (catalog.length === 0) {
      wx.showToast({ title: '暂无可配置指标', icon: 'none' });
      return;
    }

    wx.showActionSheet({
      itemList: catalog.map((x) => x.item_name),
      success: (res) => {
        const metric = catalog[res.tapIndex];
        wx.showModal({
          title: '新增别名',
          editable: true,
          placeholderText: '输入检查项别名',
          success: (modalRes) => {
            if (!modalRes.confirm) return;
            const aliasName = (modalRes.content || '').trim();
            if (!aliasName) {
              wx.showToast({ title: '请输入别名', icon: 'none' });
              return;
            }
            request({
              url: '/api/medical/mappings/aliases',
              method: 'POST',
              data: {
                dictionary_id: metric.dictionary_id,
                alias_name: aliasName,
                hospital_hint: this.data.selectedHospital || null,
                priority: this.data.selectedHospital ? 100 : 10,
              },
            })
              .then((data) => this.setData({ aliases: data.items || [] }))
              .catch((err) => wx.showToast({ title: err.msg || '新增失败', icon: 'none' }));
          },
        });
      },
    });
  },

  onEditAlias(e) {
    const id = Number(e.currentTarget.dataset.id);
    const oldName = e.currentTarget.dataset.name || '';
    wx.showModal({
      title: '修改别名',
      editable: true,
      placeholderText: '输入检查项别名',
      content: oldName,
      success: (res) => {
        if (!res.confirm) return;
        const aliasName = (res.content || '').trim();
        if (!aliasName) {
          wx.showToast({ title: '请输入别名', icon: 'none' });
          return;
        }
        request({
          url: `/api/medical/mappings/aliases/${id}`,
          method: 'PATCH',
          data: { alias_name: aliasName },
        })
          .then((data) => this.setData({ aliases: data.items || [] }))
          .catch(() => wx.showToast({ title: '修改失败', icon: 'none' }));
      },
    });
  },

  onDeleteAlias(e) {
    const id = Number(e.currentTarget.dataset.id);
    wx.showModal({
      title: '删除别名',
      content: '删除后将不再参与自动映射，是否继续？',
      success: (res) => {
        if (!res.confirm) return;
        request({
          url: `/api/medical/mappings/aliases/${id}`,
          method: 'DELETE',
        })
          .then((data) => this.setData({ aliases: data.items || [] }))
          .catch(() => wx.showToast({ title: '删除失败', icon: 'none' }));
      },
    });
  },

  onRebuild() {
    wx.showLoading({ title: '重建中' });
    request({ url: '/api/medical/mappings/rebuild', method: 'POST' })
      .then(() => {
        wx.hideLoading();
        wx.showToast({ title: '重建完成', icon: 'none' });
        this.loadAliases();
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: '重建失败', icon: 'none' });
      });
  },
});
