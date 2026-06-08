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
- 迁移：`create_all` 不补旧表列，改字段需删 `pika.db` 重建

## 验收标准

1. 多图草稿创建成功
2. 人工修正后提交成功
3. DB 可见 `hospital` 与 `image_paths`
4. 历史/详情/趋势显示 hospital
5. 真机局域网连续成功 3 次

## v0.2 工程底座（当前期）

PoC v0.1 已验证通过，本期目标是**打牢工程底座**，让后续 schema 变更与重构安全可控。按依赖排序：

1. **C1 Alembic 迁移**（基石）：替换 `create_all` 删库重建模式；C1 一通，后面所有改 schema 的 task 都不再丢数据。
2. **C2 pytest 测试骨架**：`backend/tests/`，覆盖 vision 后处理纯逻辑 + draft/commit 流程；Azure 调用 mock 掉。是后续重构的安全网。
3. **B1 删除报告接口**：`DELETE /api/medical/reports/{id}` + 历史页删除入口。改动小、不动 models，作为「首个走完整迁移+测试流程」的样板。
4. **B2 重复上传去重**（依赖 C1）：加图片内容 hash 字段，commit 时按 hash 拦截重复。
5. **C3 失败可观测**：上传失败的日志聚合/重试入口。

**依赖关系**：C1 → B2 / 后续子表化·成员管理；C2 → B1 及一切重构。C1、C2 是两个总闸。

## 后续（v0.3+）

多图子表化、草稿持久化、成员管理与共享、公网 HTTPS。
