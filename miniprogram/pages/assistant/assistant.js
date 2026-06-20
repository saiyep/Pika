const { request } = require('../../utils/request');
const { ensureLoginWithModal } = require('../../utils/auth');

Page({
  data: {
    loggedIn: false,
  },
  onShow() {
    request({ url: '/api/user/whoami' })
      .then(() => this.setData({ loggedIn: true }))
      .catch(() => {
        this.setData({ loggedIn: false });
        ensureLoginWithModal();
      });
  },
});