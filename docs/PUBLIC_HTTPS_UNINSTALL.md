# Pika 公网 HTTPS 卸载/清理指南

> 把公网 HTTPS 那一套（Azure VM 的 frps/Caddy、NAS 的 frpc、NSG 规则、微信域名配置）干净卸掉。
> 占位符含义见 `PUBLIC_HTTPS_SETUP.md`（`<VM_IP>` / `<DOMAIN>` 等）。
> 按顺序做；每段可独立执行，互不依赖。

## 0. 卸载前确认

- 卸载后家人将**无法**通过公网访问（小程序会请求失败）。开发期回退到局域网即可。
- 不影响 NAS 上的 Pika 后端本身和数据（SQLite/图片都在 NAS，不动）。

---

## 1. NAS 侧：移除 frpc

**改 docker-compose.yaml**：删掉整个 `frpc:` 服务块（`pika-frpc` 容器）。本地仓库改完 `release-backend` 同步，或直接在 NAS 改。

**删辅助文件**（可选）：
- NAS `docker/pika/frpc.toml`
- NAS `.env` 里的 `FRP_TOKEN`、`FRP_SERVER_ADDR`、`PUBLIC_DOMAIN` 三行

**重新部署**：绿联 → 项目 → pika → 重新部署。`pika-frpc` 容器消失即可。

```bash
# 如能 SSH 进 NAS，确认容器没了：
docker ps -a | grep frpc    # 应无输出
```

---

## 2. VM 侧：移除 frps 和 Caddy

SSH 进 VM（`ssh <user>@<VM_IP>`）。

### 2.1 停并删 frps 服务
```bash
sudo systemctl disable --now frps
sudo rm /etc/systemd/system/frps.service
sudo systemctl daemon-reload
rm -rf ~/frp_0.61.1_linux_amd64 ~/frp.tar.gz
```

### 2.2 卸载 Caddy
```bash
sudo systemctl disable --now caddy
sudo apt remove -y caddy
sudo rm -f /etc/apt/sources.list.d/caddy-stable.list /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo rm -rf /etc/caddy
sudo apt update
# 证书/ACME 账户缓存（可选清理）：
sudo rm -rf /var/lib/caddy ~/.local/share/caddy
```

> 注意：VM 上的 **SS（23455）和其它服务不受影响**，本指南只清 Pika 相关的 frps + Caddy。

---

## 3. Azure NSG：移除放行规则

Azure 门户 → VM → Networking → Inbound port rules，删掉为 Pika 加的：
- **7000**（`AllowFrpInbound` 之类）

> **80 / 443 视情况**：若 VM 上别的服务（n8n/SS 等）也用，**保留**；若纯为 Pika 加的，可一并删。删前确认没有其它服务依赖。

---

## 4. 微信侧：回退域名配置

- 微信公众平台 → 开发设置 → 服务器域名：移除/替换 `https://<DOMAIN>`。
- 若已发体验版且要停用：在版本管理里处理（删体验版/不再分享）。
- 小程序备案：如彻底不用了，可在公众平台注销备案（一般无需，留着无害）。

## 5. 前端回退（开发期连局域网）

`miniprogram/config.js`：
```js
const BASE_URL = 'http://192.168.1.200:8000';   // 改回 NAS 局域网 IP
```
开发者工具「详情→本地设置」勾「不校验合法域名」。

## 6. 后端 CORS 回退（可选）

`backend/app/main.py` 的 `allow_origins` 若想放开调试，临时改回 `["*"]`（注意安全）。

---

## 验证已卸载

- `https://<DOMAIN>/health` 不再可达（连接失败/超时）。
- NAS `docker ps` 无 `pika-frpc`。
- VM `systemctl status frps caddy` 均 not-found/inactive。
- 局域网 `http://192.168.1.200:8000/health` 仍正常（后端本身没动）。
