# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read first

Before coding, read:
- `docs/PROJECT_STATUS.md` (global dashboard: current truth, phase, backlog overview)
- `docs/IMPLEMENTATION_PLAN.md` (current implementation scope, shared acceptance, cross-ticket order)

If the work maps to a specific feature / bug ticket, also read the corresponding file under `docs/tickets/` before editing code or docs.

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
- `backend/app/core/`: platform-level shared capabilities (db/session, storage, base schemas/exceptions). `core/user/` holds the User model + user/member/role/favorites/profile/avatar (router at `/api/user`).
- `backend/app/modules/medical/`: medical module only (models/schemas/service/router/vision), router at `/api/medical`.

Rule: `core/` must not depend on `modules/`.

## Data and API conventions

- Unified response wrapper: `{"code": 0, "msg": "ok", "data": ...}`
- Auth (POC): `X-Pika-Token` header, token == openid
- API namespacing by layer: platform/user endpoints under `/api/user` (in `core/user/`), medical business under `/api/medical` (in `modules/medical/`), auth under `/api/auth`.
- Table naming: platform tables use generic names (`users`, `user_favorite`); module business tables use a module prefix (`medical_*`).
- Exact routes/fields are derivable from the routers — don't maintain a list here.

## Storage and deployment constraints

Persistent mounts (required, each a separate volume — `data/` itself is NOT mounted):
- Raw images: `/volume1/Projects/Pika/data/uploads/medical` -> `/app/data/uploads/medical`
- Avatars: `/volume1/Projects/Pika/data/avatars` -> `/app/data/avatars`
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
- `ADMIN_OPENID` (this openid is always role=admin on login)

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

## Documentation workflow

- `docs/PROJECT_STATUS.md` is the high-level dashboard only; keep it short.
- `docs/IMPLEMENTATION_PLAN.md` keeps scope, shared acceptance criteria, and cross-ticket execution bundles.
- `docs/tickets/TICKET_TEMPLATE.md` is the template for new tracked work items.
- For any feature / bug expected to span multiple loops, create or update one `docs/tickets/TKT-xxx-*.md` file and treat that ticket as the working unit.
