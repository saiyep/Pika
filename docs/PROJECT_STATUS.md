# Pika 项目状态（最新）

## 现状

**就医服务 PoC v0.1 验证通过；v0.2 工程底座已实现（待提交+部署）。**

PoC 主链路（多图上传→草稿→人工修正→提交→历史/详情/趋势，含 hospital）模拟器与真机均跑通，Azure 解析经人工核对正确，后端部署在绿联 NAS（`http://192.168.1.200:8000/health` 通）。

v0.2 底座五项已落地并通过 40 个 pytest：
- **C1 Alembic 迁移**：移除 `create_all`，env.py 复用 `settings.db_path`；两条迁移（initial → content_hash）。
- **C2 pytest 骨架**：`backend/tests/`，覆盖 vision 后处理 + draft/commit 流程，Azure mock。
- **B1 删除报告**：`DELETE /reports/{id}`（删库删图）+ 历史页删除按钮。
- **B2 去重**：`content_hash` 列，draft 阶段按图片内容全局判重。
- **C3 失败重解析**：`POST /reports/{id}/reparse` + 详情页重解析按钮。

## 下一步

1. **提交并部署**：commit 这批改动；release 后端到 NAS。**首次部署需对已有 `pika.db` 跑 `alembic stamp head` 再 `alembic upgrade head`**（见 CLAUDE.md）。
2. **模拟器验证前端**：删除/去重提示/重解析三个交互需部署后在微信开发者工具实测（本环境无法验 UI）。
3. （待排定 v0.3）多图子表化、草稿持久化、成员管理与共享、公网 HTTPS。

## 关键约定（易踩坑）

- DB 由 Alembic 管理；改 models 后 `alembic revision --autogenerate -m "..."` 生成迁移，启动前 `alembic upgrade head`。
- B2 去重按图片内容 hash 全局唯一；upload.js 当前每图一请求，故多图按单图判重。
- 真实凭据只在 NAS 的 `.env`，不入 git。
- 架构/命令见 `CLAUDE.md`；范围见 `IMPLEMENTATION_PLAN.md`。
