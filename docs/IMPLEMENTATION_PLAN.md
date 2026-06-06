# Pika 就医服务 POC v0.1 实施计划（最新）

> 本计划只保留当前仍在执行的方案。旧路线、过时假设、废弃逻辑已移除。

## 1. 目标

以最小可运行版本验证主链路：

小程序多图上传 -> 后端草稿预解析 -> 用户人工修正 -> 确认提交落库 -> 历史/详情/趋势可查看（含 hospital）

## 2. 本期范围（必须完成）

1. `hospital` 全链路贯通（上传、落库、查询、展示）
2. 一份报告支持多图（`image_paths`）
3. 两阶段上传流程（draft -> commit）

## 3. 本期不做（明确排除）

- 成员管理与权限细化
- 复杂订阅体系
- 公网 HTTPS 正式发布
- 多图子表化与草稿持久化表（后续再做）

## 4. 后端实施

### 4.1 数据模型

文件：`backend/app/modules/medical/models.py`

- `medical_reports` 新增：
  - `hospital`
  - `image_paths`（数组）
- 保留 `image_path` 兼容旧单图读取端点

### 4.2 API

文件：`backend/app/modules/medical/router.py`

新增：
- `POST /api/medical/report-drafts`
- `POST /api/medical/report-drafts/{draft_id}/commit`

保留兼容：
- `POST /api/medical/reports`

查询贯通：
- `/api/medical/reports`
- `/api/medical/reports/{id}`
- `/api/medical/metrics/trend`

都返回 `hospital` 相关字段。

### 4.3 服务层

文件：`backend/app/modules/medical/service.py`

- 拆分为：
  - `create_draft_from_images(...)`
  - `commit_draft(...)`
  - `create_report(...)`（兼容封装）
- 复用：
  - `core/storage.py::save_image`
  - `modules/medical/vision.py::parse_report_image`

### 4.4 Schema

文件：`backend/app/modules/medical/schemas.py`

- 补充 hospital 字段到报告/趋势结构
- 增加 Draft 相关 schema

## 5. 小程序实施

### 5.1 上传页

文件：
- `miniprogram/pages/medical/upload/upload.js`
- `miniprogram/pages/medical/upload/upload.wxml`
- `miniprogram/pages/medical/upload/upload.wxss`

改动：
- 支持多图选择
- 调 draft 接口获取可编辑结果
- 人工修正后调用 commit 提交

### 5.2 历史 / 详情 / 趋势

文件：
- `miniprogram/pages/medical/history/history.wxml`
- `miniprogram/pages/medical/report-detail/report-detail.wxml`
- `miniprogram/pages/medical/metric-trend/*`

改动：
- 展示 hospital
- 趋势按医院来源区分显示

## 6. 部署与运行要求

### 6.1 持久化挂载

- `/volume1/Projects/Pika/data/uploads/medical` -> `/app/data/uploads/medical`
- `/volume1/Projects/Pika/data/db` -> `/app/data/db`

### 6.2 环境变量（真实值）

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`
- `WX_APPID`
- `WX_SECRET`

### 6.3 迁移策略（POC）

当前使用 `create_all`，不会自动给旧表补列。若旧 `pika.db` 缺新字段，直接重建 DB。

## 7. 验收标准

必须全部通过：

1. 草稿创建成功（多图）
2. 草稿提交成功（人工修正后）
3. 数据库可见 `hospital` 与 `image_paths`
4. 历史/详情/趋势能看到 hospital
5. 真机（局域网）链路可连续成功 3 次

## 8. 下一步（完成本期后）

1. NAS 真环境稳定化（日志、异常回放）
2. 真实单据解析质量调优（prompt + 后处理）
3. 多图子表化与草稿持久化
4. 成员管理与共享模型
5. 公网发布链路
