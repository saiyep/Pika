// 默认连局域网 NAS（开发者工具需勾「不校验合法域名」）。
// 要连公网 HTTPS：复制 config.local.example.js 为 config.local.js 并填域名，
// config.local.js 已被 gitignore，不会进仓库。
let BASE_URL = 'http://192.168.1.200:8000';

try {
  // 本地覆盖（存在则用它，不存在不报错）
  const local = require('./config.local');
  if (local && local.BASE_URL) {
    BASE_URL = local.BASE_URL;
  }
} catch (_e) {
  // 没有 config.local.js，用默认
}

module.exports = {
  BASE_URL,
};
