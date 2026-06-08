# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read first

Before coding, read:
- `docs/PROJECT_STATUS.md` (current truth, progress, blockers, next steps)
- `docs/IMPLEMENTATION_PLAN.md` (current implementation scope and execution order)

## Project scope (current)

Pika is a self-hosted family service platform running on a home NAS. The current active module is **就医服务** (medical check-up tracking).

POC v0.1 scope (current and authoritative):
1. `hospital` is required and must be persisted/displayed end-to-end.
2. One report can contain **multiple images**.
3. Upload flow is **two-stage**: draft parse first, user edits, then commit.

Not in current scope:
- family member management UI/permission model
- complex subscription system
- public HTTPS production rollout

## Architecture (authoritative)

Mini Program (native WeChat) -> FastAPI backend -> SQLite + NAS file storage -> Azure GPT-4.5-mini (vision)

Backend layering:
- `backend/app/core/`: platform-level shared capabilities (db/session, user resolution, storage, base schemas/exceptions)
- `backend/app/modules/medical/`: medical module only (models/schemas/service/router/vision)

Rule: `core/` must not depend on `modules/`.

## Data and API conventions

- Unified response wrapper: `{"code": 0, "msg": "ok", "data": ...}`
- Auth (POC): `X-Pika-Token` header, token == openid
- Table naming: module business tables must use `medical_` prefix

Current key medical APIs:
- `POST /api/medical/report-drafts`
- `POST /api/medical/report-drafts/{draft_id}/commit`
- `POST /api/medical/reports` (compat path)
- `GET /api/medical/reports`
- `GET /api/medical/reports/{id}`
- `GET /api/medical/reports/{id}/image`
- `GET /api/medical/metrics/catalog`
- `GET /api/medical/metrics/trend`

## Storage and deployment constraints

Persistent mounts (required):
- Raw images: `/volume1/Projects/Pika/data/uploads/medical` -> `/app/data/uploads/medical`
- SQLite DB: `/volume1/Projects/Pika/data/db` -> `/app/data/db`

Important UGREEN Docker UI constraint:
- `docker-compose.yml` must keep `build.context: .`
- Project files must be placed inside the NAS shared directory used by UGREEN Docker UI

## Secrets policy (current)

Do not store real secrets in repo files.
Inject runtime env vars in NAS compose environment:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`
- `WX_APPID`
- `WX_SECRET`

## Local development commands

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# cmd: .venv\Scripts\activate.bat
# bash/zsh: source .venv/bin/activate
pip install -r requirements.txt

DATA_DIR=./data UPLOAD_DIR=./data/uploads/medical DB_PATH=./data/db/pika.db alembic upgrade head
DATA_DIR=./data UPLOAD_DIR=./data/uploads/medical DB_PATH=./data/db/pika.db uvicorn app.main:app --reload
```

Health check:
```bash
curl http://127.0.0.1:8000/health
```

Tests:
```bash
cd backend && pytest          # vision post-processing + draft/commit flow (Azure mocked)
```

Docker local:
```bash
docker compose up --build
```

## DB migration (Alembic)

Schema is managed by Alembic (`backend/alembic/`). `create_all` is gone — the app no longer builds tables on startup. `alembic/env.py` reads the DB URL from `settings.db_path`, so local and NAS use the same wiring.

Workflow (run inside `backend/`):
```bash
alembic upgrade head                          # apply migrations (run before first start / after pull)
alembic revision --autogenerate -m "message"  # after editing models.py, generate a migration
alembic downgrade -1                           # roll back one
```

NAS note: the existing `pika.db` predates Alembic. Stamp it once so Alembic treats it as current, then upgrade normally going forward:
```bash
alembic stamp head    # ONLY the first time, on the pre-existing NAS DB
```

## Mini Program runtime note

- DevTools must enable “不校验合法域名” for LAN HTTP POC.
- `miniprogram/project.config.json` still requires a real AppID before full device flow.
