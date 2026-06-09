# Pika 就医服务 POC v0.1 实施计划

> 实时进度看 `PROJECT_STATUS.md`；本文件定义范围与验收口径。

## 目标

验证主链路：小程序多图上传 → 后端草稿预解析 → 人工修正 → 提交落库 → 历史/详情/趋势可查（含 hospital）。

## 本期范围

1. `hospital` 全链路贯通（上传/落库/查询/展示）
2. 一份报告多图（`image_paths`，保留 `image_path` 兼容首图）
3. 两阶段上传（`report-drafts` 预解析 → `commit`），保留 `POST /reports` 兼容

**不做**：成员管理、复杂订阅、公网发布、多图子表化/草稿持久化（均后续）。

## 部署要求

- 挂载：`/volume1/Projects/Pika/data/uploads/medical` 与 `/data/db` → 容器 `/app/data/...`
- 环境变量（NAS `.env`）：`WX_APPID/WX_SECRET` + `AZURE_OPENAI_ENDPOINT/API_KEY/API_VERSION/DEPLOYMENT`
- 迁移：Alembic 管理；NAS 首次 `alembic stamp head` 后续 `alembic upgrade head`

## 验收标准

1. 多图草稿创建成功
2. 人工修正后提交成功
3. DB 可见 `hospital` 与 `image_paths`
4. 历史/详情/趋势显示 hospital
5. 真机局域网连续成功 3 次

## 已完成（PoC v0.1 + v0.2 底座 + 平台化）

PoC 主链路、v0.2 工程底座（Alembic/pytest/删除/去重/重解析）均已实现验证。其后又落地：成员档案（报告按被检查人归属+筛选）、底部 TabBar+服务市场、成员角色（ADMIN_OPENID）、微信昵称头像、历史多 filter、`core/user/` 平台子模块重构。全部部署到 NAS 并经用户验证。当前能力清单见 `PROJECT_STATUS.md` 与 memory。

## 下一步（按优先级）

1. **公网 HTTPS + 体验版**（最高）：多用户功能已就绪，被「仅 admin 能登录」卡着；公网就绪后家人登录即激活。涉及域名/内网穿透/证书/微信后台。
2. 二维码邀请（依赖 1）、权限控制（依赖多用户）。
3. 趋势图升级、AI 助手（中间 tab）、更多报告类型适配。
