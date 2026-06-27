---
name: release-backend
description: 把 Pika 后端通过 SSH 发布到 NAS 的 `/volume1/docker/pika`。同步 Dockerfile + backend/ + docker-compose.yaml（及本次改动所需的部署文件），保护已有 `.env`，然后调用 NAS 上 `/home/pika/bin/deploy_pika_backend.sh` 完成一键部署、Alembic 升级与 `/health` 校验。当用户说"release后端""部署后端""更新NAS服务""发版"时使用。
---

# Release Backend to NAS (Pika)

把仓库最新后端同步到 NAS 部署目录，并直接触发 NAS 侧一键部署脚本。

## 关键事实
- NAS SSH：`pika@192.168.1.200`
- 允许操作边界：`/home/pika`、`/volume1/docker/pika`、Pika 自身 Docker 资源。
- NAS 部署目录：`/volume1/docker/pika`
- NAS 部署脚本：`/home/pika/bin/deploy_pika_backend.sh`
- 绿联仍以该目录 `docker-compose.yaml` 部署，且必须保持 `build.context: .`，所以 `Dockerfile` + `backend/` 必须同目录。
- 真实凭据只保留在 NAS 的 `.env`（不入 git）；健康检查目标仍是 `http://192.168.1.200:8000/health`。
- 该脚本已负责：`docker compose up -d --build`、`docker compose exec -T pika-backend alembic upgrade head`、健康检查。

## 红线
- 不操作边界外路径。
- 不覆盖/删除 NAS 的 `.env`。
- 不把真实密钥写进仓库文件。
- 不复制 `backend/data/`、`.venv/`、`.git/`、`__pycache__/`。
- 不再停留在“只复制文件”；发布后要实际调用 NAS 脚本完成部署。
- 非排障场景，不手工分拆执行 compose / migration / health check，优先复用既有脚本。

## 步骤
1. 本地自检：`python -m compileall backend/app`。
2. 同步：把 `Dockerfile`、`backend/`、`docker-compose.yaml` 以及本次改动直接依赖的部署文件同步到 `/volume1/docker/pika`；可用 SSH 复制（如 `scp` / `rsync over SSH`）或等价方式，但只覆盖目标文件，不碰 `.env`。
3. 远端校验：通过 SSH 确认目标文件到位、compose 仍使用 `${...}` 占位、未引入明文密钥。
4. 部署：执行 `ssh pika@192.168.1.200 /home/pika/bin/deploy_pika_backend.sh`，以脚本完成重建、迁移与健康检查。
5. 若脚本失败，明确区分是“同步失败 / 部署失败 / 迁移失败 / 健康检查失败”，停止继续操作并回报。
6. 简报：同步了哪些文件、是否动了 compose、是否预期有 Alembic 迁移、脚本执行结果与 `/health` 结果。
