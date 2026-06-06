---
name: release-backend
description: 把 Pika 后端代码发布(部署)到绿联 NAS 的 Docker 项目目录。当用户说"release后端""部署后端""更新NAS上的服务""发版"时使用。会把最新的 Dockerfile + backend/ + docker-compose.yaml 同步到 NAS 共享目录，保护 NAS 上已存在的 .env，并指引在绿联界面重新部署、验证 /health。
---

# Release Backend to NAS (Pika)

把仓库里最新的后端代码发布到绿联 NAS 的 Docker 项目目录，使其可被绿联「项目/Compose」重新部署。

## 关键事实（部署约定）
- NAS 项目目录（UNC，Claude 有直接读写权限）：`//DH4300PLUS-D2E0/docker/pika`
- 绿联用该目录的 `docker-compose.yaml` 部署；`build.context: .` 要求 `Dockerfile` 与 `backend/` 都在该目录。
- **compose 文件名两边统一为 `docker-compose.yaml`**（仓库与 NAS 同名，直接复制即可）。NAS 目录里只应有这一个 compose 文件，若发现历史遗留的 `docker-compose.yml` 要删掉，避免绿联读错。
- 真实凭据放该目录 `.env`（不入 git），compose 用 `${...}` 占位注入。
- 端口 `8000:8000`；健康检查 `http://192.168.1.100:8000/health`。

## 绝对不能做
- **不要覆盖 / 删除 NAS 上的 `.env`**（里面是用户真实密钥）。
- 不要把任何真实密钥写进仓库文件。
- 不要把 `backend/data/`、`.venv/`、`.git/`、`__pycache__/` 复制到 NAS。

## 执行步骤

1. **本地自检**：
   - `python -m compileall backend/app` 确认后端无语法错误。
2. **确认 NAS 目录可达并查看现状**：
   - `ls -la //DH4300PLUS-D2E0/docker/pika`
   - 确认 `.env` 是否存在（存在则必须保留）。
3. **同步代码到 NAS**（覆盖式复制，但排除数据/虚拟环境/git）：
   - 复制 `Dockerfile` → NAS 根
   - 复制整个 `backend/`（仅源码：`requirements.txt`、`.env.example`、`app/**` 的 .py），排除 `backend/data`、`__pycache__`
   - compose 文件处理（两边同名 `docker-compose.yaml`）：
     - 默认**不动** NAS 的 `docker-compose.yaml`——它已是 `${...}` 占位 + 资源限制的正确结构。
     - 仅当仓库 `docker-compose.yaml` 有**实质结构变化**（端口、挂载、环境变量项、资源限制等）时才复制覆盖到 NAS，并保持全部 `environment` 用 `${...}` 占位。
     - 若 NAS 目录里存在历史遗留的 `docker-compose.yml`，删除它，确保只有 `docker-compose.yaml` 一个 compose 文件。
4. **校验 NAS 目录结构**：
   - `find //DH4300PLUS-D2E0/docker/pika -type f` 确认 `Dockerfile`、`backend/app/main.py`、`docker-compose.yaml`、`.env` 都在。
   - `ls //DH4300PLUS-D2E0/docker/pika/docker-compose.*` 应只列出 `docker-compose.yaml`（不能同时有 `.yml`）。
   - `grep -nE 'PUT_YOUR|<真实key特征>' //DH4300PLUS-D2E0/docker/pika/docker-compose.yaml` 确认 compose 无明文密钥。
5. **DB 迁移提醒**：
   - 后端用 `create_all`，新增列不会自动加到旧表。
   - 若本次改了 `models.py` 字段：提醒用户 POC 阶段需删 NAS 上 `/volume1/Projects/Pika/data/db/pika.db` 让其重建（这会清空已有数据，必须先征求用户确认）。
6. **指引部署 + 验证**（这步在绿联界面，由用户点）：
   - 让用户去绿联「项目」页对 pika 项目执行重新部署/重建。
   - 部署后验证：浏览器或 curl `http://192.168.1.100:8000/health` 应返回 `{"code":0,...,"service":"pika-backend"}`。
7. **简报**：列出本次同步了哪些文件、是否动了 compose、是否需要重建 DB、以及验证结果。

## 备注
- 这是 POC 部署流程；镜像构建在绿联侧完成，Claude 侧只负责把正确文件放到位 + 指引。
- 若 Azure / 微信凭据有变更，提醒用户改的是 NAS 的 `.env`，不是仓库。
