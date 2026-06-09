# Pika 公网 HTTPS 部署手册（Azure VM + frp + Caddy）

> 让微信小程序体验版/正式版能访问跑在家用 NAS 上的 Pika 后端。
> 微信要求 HTTPS 合法域名（不能用局域网 IP/HTTP），而家宽无公网 IP（内网），
> 所以用一台 Azure VM 做公网入口，frp 内网穿透把 NAS 的后端透出去，Caddy 自动出 HTTPS 证书。

## 占位符（实际值见 NAS `.env`，不入 git）

| 占位 | 含义 |
|---|---|
| `<VM_IP>` | Azure VM 公网 IP |
| `<DOMAIN>` | 对外域名（Azure VM 自带的 `*.cloudapp.azure.com`，或自购域名） |
| `<FRP_TOKEN>` | frps/frpc 共享认证密钥（`openssl rand -hex 16` 生成） |
| `<HOME_IP_CIDR>` | 家宽出口 IP 段（如 `120.245.128.0/19`），用于 NSG 限制来源 |

## 架构

```
家人微信小程序
  → https://<DOMAIN>            (Azure VM: Caddy 监听 443，自动 Let's Encrypt 证书)
  → 127.0.0.1:8080             (VM 本机: frps vhostHTTPPort)
  → [frp 隧道, TLS 加密, :7000] (NAS 的 frpc 主动外连进来)
  → http://pika-backend:8000   (NAS: pika-backend 容器)
```

要点：NAS 侧 **frpc 主动外连** VM（家宽无需公网 IP/端口转发）；隧道用 token 认证 + TLS 加密；NSG 把 7000 限制到家宽 IP 段。

## 前置条件

- 一台 Azure Linux VM（Ubuntu 22.04），有固定公网 IP，区域选境外（如 East Asia/香港 → 域名免 ICP 备案、延迟低）。
- VM 自带域名 `*.cloudapp.azure.com`（Azure 免费分配）即可，无需另购域名。
- NAS 上 Pika 已用 docker-compose 部署（`pika-backend` 容器）。

---

## A. VM 侧（一次性）

SSH 进 VM（`ssh <user>@<VM_IP>`）。

### A1. 装 frp（隧道服务端 frps）

```bash
cd ~
curl -L -o frp.tar.gz https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz
tar -xzf frp.tar.gz
cd frp_0.61.1_linux_amd64
```

生成 token（记下来，NAS 要用同一个）：
```bash
openssl rand -hex 16   # 输出即 <FRP_TOKEN>
```

写 `frps.toml`：
```toml
bindPort = 7000
vhostHTTPPort = 8080
auth.method = "token"
auth.token = "<FRP_TOKEN>"
transport.tls.force = true   # 只接受 TLS 连接
```

做成开机自启服务：
```bash
sudo tee /etc/systemd/system/frps.service <<EOF
[Unit]
Description=frp server
After=network.target
[Service]
Type=simple
ExecStart=$HOME/frp_0.61.1_linux_amd64/frps -c $HOME/frp_0.61.1_linux_amd64/frps.toml
Restart=on-failure
RestartSec=5
User=$USER
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now frps
sudo systemctl status frps --no-pager    # 应 active(running)
```

### A2. 装 Caddy（自动 HTTPS）

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

配 `/etc/caddy/Caddyfile`：
```
<DOMAIN> {
    reverse_proxy 127.0.0.1:8080
}
```

```bash
sudo systemctl reload caddy
sudo journalctl -u caddy -n 30 --no-pager   # 看到 "certificate obtained successfully" 即成功
```

### A3. Azure NSG 放行端口

Azure 门户 → VM → Networking → Inbound port rules，确保有：
- **80** TCP（Caddy ACME 验证）— 一般已有
- **443** TCP（HTTPS）— 一般已有
- **7000** TCP（frp）—— **新增**，Source 限到 `<HOME_IP_CIDR>`（家宽出口 IP 段，比 Any 安全）

> 家宽出口 IP 查询：在家里访问 `https://ifconfig.me`。IP 会浮动，用 `/19` 这类掩码覆盖城域网段；跳出范围就更新该规则。

---

## B. NAS 侧（纳入 Pika 仓库，可 release）

仓库里已有（随 `release-backend` 一起同步）：
- `frpc.toml`：全占位符（serverAddr/token/域名都从环境变量读），无敏感信息，已入库。
- `docker-compose.yaml`：含 `frpc` 服务。

NAS 的 `.env` 需有（**不入 git**）：
```
FRP_TOKEN=<FRP_TOKEN>
FRP_SERVER_ADDR=<VM_IP>
PUBLIC_DOMAIN=<DOMAIN>
```

部署：绿联 → 项目 → pika → 重新部署。frpc 容器（`pika-frpc`）应稳定运行、不重启。

---

## C. 验证全链路

```bash
# VM 上看 frps：应有 client login + new proxy [pika] success
sudo journalctl -u frps -n 20 --no-pager
```

```bash
# 任意网络打开（注意本机若开代理且 PAC 把该域名走代理可能影响，测时可禁用代理）
curl https://<DOMAIN>/health
# 期望: {"code":0,"msg":"ok","data":{"service":"pika-backend","version":"...","db_revision":"..."}}
```

frpc 容器日志应有 `login to server success` + `start proxy success`。

---

## D. 微信侧（让家人真正用上）

1. **小程序本身备案**（2023.9 起强制，境内外都要）：微信公众平台 → 小程序备案。耗时项，尽早办。
2. **服务器域名**：开发管理 → 开发设置 → 服务器域名，request/uploadFile/downloadFile 三类都填 `https://<DOMAIN>`。
   - ⚠️ 不确定微信是否接受 `*.cloudapp.azure.com` 云厂商子域名；不接受就买个自有域名解析到 `<VM_IP>`。
3. `miniprogram/config.js` 的 `BASE_URL` 已改成 `https://<DOMAIN>`。
4. 上传 → 设为体验版 → 加家人为体验成员（个人号约 15 名）。

---

## 故障排查

| 现象 | 原因 | 解法 |
|---|---|---|
| 域名打开显示 frp 的 "page not found" | frpc 没连上 frps（隧道没建） | 看 frpc 日志；多半是 NSG 没放行 7000，或 token 不一致 |
| frpc 日志 `dial ...:7000 i/o timeout` | NSG 没放行 7000，或 Source IP 段不含当前家宽 IP | 加/改 NSG 7000 规则，Source 含当前出口 IP |
| frpc `token doesn't match` | 两端 token 不一致 | 核对 VM `frps.toml` 与 NAS `.env` 的 token |
| 域名 502 | Caddy 通但 frps 没起 / 8080 不通 | `systemctl status frps`，确认 8080 监听 |
| 证书申请失败 | 80 端口不可达 / 域名解析错 | 确认 NSG 放行 80、域名解析到 `<VM_IP>` |
| frpc 反复重启 | 配置错 / 连不上且 loginFailExit | 看日志定位；改对后 NAS 重新部署 |

## 安全说明

- frp 隧道：token 认证 + TLS 加密；NSG 把 7000 限到家宽 IP 段。
- 后端 CORS 已收紧到 `<DOMAIN>`（浏览器侧；微信请求不走浏览器 CORS）。
- ⚠️ 当前后端 **POC 无鉴权**（任何持 openid 的请求都接受）。公网暴露后这是主要风险点，后续应加访问控制。
- 真实凭据（token/IP/密钥）只在 NAS `.env`，不入 git。
