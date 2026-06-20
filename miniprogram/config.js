// 默认连公网 HTTPS（体验版/线上）。
// 仅开发环境允许本地 config.local.js 覆盖到局域网地址。
let BASE_URL = 'https://pika-n8n.eastasia.cloudapp.azure.com';

let envVersion = 'release';
try {
  const account = wx.getAccountInfoSync();
  envVersion = (account && account.miniProgram && account.miniProgram.envVersion) || 'release';
} catch (_e) {}

if (envVersion === 'develop') {
  try {
    const local = require('./config.local');
    if (local && local.BASE_URL) {
      BASE_URL = local.BASE_URL;
    }
  } catch (_e) {}
}

module.exports = {
  BASE_URL,
};
