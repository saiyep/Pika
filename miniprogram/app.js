const { login } = require('./utils/auth');

App({
  globalData: {
    token: '',
    user: null,
  },
  onLaunch() {
    login()
      .then((res) => {
        this.globalData.token = res.token;
        this.globalData.user = res.user;
      })
      .catch((err) => {
        console.error('login failed', err);
      });
  },
});
