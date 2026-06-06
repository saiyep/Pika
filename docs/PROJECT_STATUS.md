# Pika 项目状态（最新）

> 本文件只保留当前有效逻辑、需求与下一步。历史废弃方案已移除。

## 一句话现状

当前项目主线是 **就医服务 POC v0.1**：
- `hospital` 字段已纳入主流程
- 支持一份报告多图上传（`image_paths`）
- 上传改为两阶段（草稿预解析 -> 人工修正 -> 确认提交）

本地接口链路已跑通；NAS 真机链路仍待完成。

## 当前有效需求（唯一口径）

1. 以就医服务为首个可运行模块。
2. 数据必须可追踪：报告、指标、医院来源、时间维度。
3. 多图上传必须可用（长截图分段场景）。
4. 识别结果必须允许人工修正后再提交。
5. 趋势页支持医院来源区分；数值呈现按当前确认规则执行。

## 当前已完成

### 后端
- `medical_reports` 增加：
  - `hospital`
  - `image_paths`（同时保留 `image_path` 兼容旧逻辑）
- 新增两阶段接口：
  - `POST /api/medical/report-drafts`
  - `POST /api/medical/report-drafts/{draft_id}/commit`
- 保留兼容接口：
  - `POST /api/medical/reports`
- 查询接口贯通 `hospital`：
  - 列表、详情、趋势点
- 本地编译检查通过；本地 API 链路验证通过（draft -> commit -> list/detail/trend）。

### 小程序
- 上传页改为：多图选择 + 草稿编辑后提交。
- 历史页、详情页展示 hospital。
- 趋势页点位按 hospital 区分显示，并展示来源信息。

## 当前待办（下一步按优先级）

1. **NAS 部署恢复与挂载核验**
   - 确认挂载生效：
     - `/volume1/Projects/Pika/data/uploads/medical`
     - `/volume1/Projects/Pika/data/db`
2. **注入真实凭据**（NAS compose environment）
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_API_VERSION`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `WX_APPID`
   - `WX_SECRET`
3. **小程序配置与真机联调**
   - 注册并填写真实 AppID（`miniprogram/project.config.json`）
   - `miniprogram/config.js` 指向 NAS 局域网 IP
   - DevTools 开启“不校验合法域名”
4. **验收 POC 主链路**
   - 多图上传 -> 预解析草稿 -> 人工修正 -> 提交
   - 历史/详情/趋势可见 hospital
5. **解析质量调优**
   - 用真实检查单调 `prompts.py` 与后处理

## 当前阻塞项

- 未完成 NAS 真环境凭据注入
- 小程序 AppID 仍为占位符
- 未完成真机端到端回归

## 关键路径文件

- 后端入口：`backend/app/main.py`
- 医疗路由：`backend/app/modules/medical/router.py`
- 医疗编排：`backend/app/modules/medical/service.py`
- 医疗模型：`backend/app/modules/medical/models.py`
- 医疗 schema：`backend/app/modules/medical/schemas.py`
- 视觉解析：`backend/app/modules/medical/vision.py`
- 小程序上传页：`miniprogram/pages/medical/upload/*`
- 小程序历史/详情/趋势：`miniprogram/pages/medical/history/*`、`report-detail/*`、`metric-trend/*`
- 部署文件：`docker-compose.yml`、`Dockerfile`

## 验证命令（本地）

```bash
cd backend
python -m venv .venv
# 激活虚拟环境
pip install -r requirements.txt
DATA_DIR=./data UPLOAD_DIR=./data/uploads/medical DB_PATH=./data/db/pika.db uvicorn app.main:app --reload
```

健康检查：
```bash
curl http://127.0.0.1:8000/health
```

说明：当前使用 `create_all`，若旧 DB 存在且缺新列，需重建 `pika.db`。
