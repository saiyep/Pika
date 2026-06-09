# Pika 项目状态（最新）

## 现状

**就医服务模块已相当完整，平台化框架（TabBar+服务市场+成员/角色）已落地，全部部署到 NAS 并验证。**

已实现并验证的能力（详见 `memory` 与代码）：
- **就医**：多图上传→草稿→人工修正→提交→历史/详情/趋势（含 hospital）；删除、重复去重、失败重解析、防误传、医院预设、详情页可编辑（含改被检查者）。
- **成员档案**：报告按被检查人（subject=登录用户）归属；历史/趋势按人筛选；历史多 filter（被检查者/医院/时间范围）。
- **平台化**：底部 TabBar（服务市场/AI助手占位/我）；成员管理 + 角色（ADMIN_OPENID→admin）；微信昵称头像（"我"页设置，存 NAS data/avatars）。
- **工程底座**：Alembic 迁移、pytest（50+ 测试）、日志时间戳、密钥不落日志、`/health` 带 version+db_revision。

后端 `core/`（平台，`/api/user`）+ `modules/medical/`（就医，`/api/medical`）分层；用户相关在 `core/user/` 子模块。

## 下一步（按优先级）

1. **公网 HTTPS 已打通** ✅：Azure VM + frp + Caddy，`https://<域名>/health` 公网可达（手册见 `PUBLIC_HTTPS_SETUP.md`）。**剩微信侧让家人登录**：① 小程序备案（耗时，尽早办）② 微信后台填合法域名（实测云域名 `*.cloudapp.azure.com` 是否被接受）③ 发体验版 + 加家人为体验成员。家人登录后所有多用户功能即激活。
2. **二维码邀请加入**（依赖家人能登录后）。
3. **权限控制**（依赖多用户）：普通用户不能删/改别人报告、改别人角色。
4. **趋势图升级**、**AI 助手**（中间 tab，自然语言查数据）、更多报告类型适配。
5. **安全收尾**：后端当前 POC 无鉴权，公网暴露后是主要风险点，应加访问控制。

## 关键约定（易踩坑）

- DB 由 Alembic 管理；改 models 后 `alembic revision --autogenerate`。NAS 部署 entrypoint 自动 upgrade。
- 改 backend 代码须 **rebuild**（重启不够）；改挂载须同步 NAS 的 `docker-compose.yaml`。
- 流程：先 release→模拟器验证→再 commit（不提交未验证代码）。
- ADMIN_OPENID 等真实凭据只在 NAS `.env`，不入 git。
- 架构/命令见 `CLAUDE.md`。
