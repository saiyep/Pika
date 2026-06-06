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

## 后续（v0.2+）

多图子表化、草稿持久化、成员管理与共享、公网 HTTPS。
