const { request } = require('../../../utils/request');

Page({
  data: {
    categories: [],
  },

  onShow() {
    this.loadCategories();
  },

  loadCategories() {
    request({ url: '/api/medical/categories' })
      .then((data) => this.setData({ categories: data.items || [] }))
      .catch(() => wx.showToast({ title: '加载失败', icon: 'none' }));
  },

  onAddCategory() {
    wx.showModal({
      title: '新增检查单分类',
      editable: true,
      placeholderText: '请输入分类名称',
      success: (res) => {
        if (!res.confirm) return;
        const name = (res.content || '').trim();
        if (!name) {
          wx.showToast({ title: '请输入分类名称', icon: 'none' });
          return;
        }
        request({
          url: '/api/medical/categories',
          method: 'POST',
          data: { display_name: name },
        })
          .then((data) => this.setData({ categories: data.items || [] }))
          .catch(() => wx.showToast({ title: '新增失败', icon: 'none' }));
      },
    });
  },

  onRenameCategory(e) {
    const id = Number(e.currentTarget.dataset.id);
    const oldName = e.currentTarget.dataset.name || '';
    wx.showModal({
      title: '修改检查单分类',
      editable: true,
      placeholderText: '请输入分类名称',
      content: oldName,
      success: (res) => {
        if (!res.confirm) return;
        const name = (res.content || '').trim();
        if (!name) {
          wx.showToast({ title: '请输入分类名称', icon: 'none' });
          return;
        }
        request({
          url: `/api/medical/categories/${id}`,
          method: 'PATCH',
          data: { display_name: name },
        })
          .then((data) => this.setData({ categories: data.items || [] }))
          .catch(() => wx.showToast({ title: '修改失败', icon: 'none' }));
      },
    });
  },

  onDeleteCategory(e) {
    const id = Number(e.currentTarget.dataset.id);
    wx.showModal({
      title: '删除检查单分类',
      content: '删除后将不再显示该分类，是否继续？',
      success: (res) => {
        if (!res.confirm) return;
        request({
          url: `/api/medical/categories/${id}`,
          method: 'DELETE',
        })
          .then((data) => this.setData({ categories: data.items || [] }))
          .catch(() => wx.showToast({ title: '删除失败', icon: 'none' }));
      },
    });
  },
});
