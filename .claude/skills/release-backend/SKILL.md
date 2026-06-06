---
name: release-backend
description: 把 Pika 后端代码发布到绿联 NAS 的 Docker 项目目录。当用户说"release后端""部署后端""更新NAS服务""发版"时使用。同步 Dockerfile + backend/ + docker-compose.yaml 到 NAS，保护已有 .env，指引绿联重新部署并验证 /health。
---

# Release Backend to NAS (Pika)

把仓库最新后端同步到 NAS 目录，供绿联「项目/Compose」重新部署。

## 关键事实
- NAS 目录（Claude 有直接读写权限）：`//DH4300PLUS-D2E0/docker/pika`
- 绿联用该目录 `docker-compose.yaml` 部署，`build.context: .` 要求 `Dockerfile`+`backend/` 同在该目录。
- compose 仓库与 NAS 同名 `docker-compose.yaml`，直接复制即可；NAS 目录只应有这一个 compose 文件（遗留的 `.yml` 要删）。
- 真实凭据在该目录 `.env`（不入 git），compose 用 `${...}` 占位。端口 8000；健康检查 `http://192.168.1.100:8000/health`。

## 红线
- 不覆盖/删除 NAS 的 `.env`。
- 不把真实密钥写进仓库文件。
- 不复制 `backend/data/`、`.venv/`、`.git/`、`__pycache__/`。

## 步骤
1. 本地自检：`python -m compileall backend/app`。
2. 同步：复制 `Dockerfile` 和 `backend/`（仅源码）到 NAS；compose 默认不动，仅当仓库 compose 结构变了才覆盖（保持 `${...}` 占位）。
3. 校验：`find //DH4300PLUS-D2E0/docker/pika -type f` 确认关键文件齐全；确认 compose 只有 `.yaml` 一个且无明文密钥。
4. DB 迁移：若改了 `models.py` 字段，提醒用户需删 NAS 上 `pika.db` 重建（清数据，**先征得同意**）。
5. 指引用户在绿联「项目」页重新部署，然后验证 `/health` 返回 `{"code":0,...}`。
6. 简报：同步了哪些文件、是否动 compose、是否需重建 DB、验证结果。
