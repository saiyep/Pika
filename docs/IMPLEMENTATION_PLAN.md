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

## v0.2 工程底座（已完成）

PoC v0.1 验证通过后，本期打牢工程底座，让 schema 变更与重构安全可控。五项均已实现并通过 pytest：

1. **C1 Alembic 迁移** — 替换 `create_all`，env.py 复用 `settings.db_path`。
2. **C2 pytest 测试骨架** — `backend/tests/`，vision 后处理 + draft/commit 流程（Azure mock）。
3. **B1 删除报告** — `DELETE /reports/{id}`（删库删图）+ 历史页删除。
4. **B2 重复上传去重** — `content_hash` 列，draft 阶段按图片内容全局判重。
5. **C3 失败重解析** — `POST /reports/{id}/reparse`，对 failed 报告用原图重调 Azure。

## 后续（v0.3+，待排定）

多图子表化、草稿持久化、成员管理与共享、公网 HTTPS。
