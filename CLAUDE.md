# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Continuing context

For project status, history, decisions, and the to-do list, read **`docs/PROJECT_STATUS.md`** first. The full design plan is in `docs/IMPLEMENTATION_PLAN.md`.

## Project Overview

**Pika** is a self-hosted **family service platform** running on a home NAS (UGREEN DH4300plus, Docker). It is designed to grow module by module; the first module is a **medical visit assistant** for tracking a family member's medical check-up records.

Core flow of the medical module: a family member uploads a photo of a medical report (e.g. blood routine) via a WeChat Mini Program → the FastAPI backend stores the raw image on the NAS and calls Azure GPT-4.5-mini (vision) to extract structured data → results are stored in SQLite → the Mini Program shows a dashboard with history and per-metric trends.

## Architecture

```
miniprogram/  (WeChat Mini Program, native)
      |  HTTP (LAN POC: http://<nas-ip>:8000)
      v
backend/app/
├── core/          # platform-wide capabilities, shared across modules
│   ├── db.py            # SQLAlchemy engine / SessionLocal / Base / get_db
│   ├── models_base.py   # User table (WeChat openid) + TimestampMixin
│   ├── deps.py          # current-user resolution (X-Pika-Token header)
│   ├── wechat.py        # wx.login code -> openid (jscode2session)
│   ├── storage.py       # raw image persistence (path/naming/save/read)
│   ├── schemas_base.py  # unified ApiResponse wrapper
│   └── exceptions.py
└── modules/
    └── medical/   # medical module (may depend on core)
        ├── router.py     # /api/medical/* endpoints
        ├── models.py     # MedicalReport / MedicalReportMetric
        ├── schemas.py
        ├── service.py    # orchestration: store image -> vision -> persist
        ├── vision.py     # Azure GPT-4.5-mini vision call + JSON fallback
        └── prompts.py
```

**Layering rule**: `core/` must NOT depend on `modules/`. New modules go under `modules/<name>/` and are mounted in `app/main.py`; do not modify existing modules to add a new one.

## Conventions

- **DB table naming**: platform-level tables (e.g. `users`) live in core with generic names. **Module business tables MUST be prefixed with the module name** (medical → `medical_reports`, `medical_report_metrics`). Future modules follow `<module>_` prefixing to avoid collisions.
- **API paths**: module-prefixed, e.g. `/api/medical/...`.
- **Unified response**: `{"code": 0, "msg": "ok", "data": {...}}`; `code != 0` means business error.
- **Auth (POC)**: WeChat `wx.login` code → backend swaps for `openid` via `jscode2session`. Token (POC: token == openid) passed in `X-Pika-Token` header. No permissions — the whole family shares read/write; the user table is only for identifying & displaying who uploaded/whose report.
- **Secrets**: never commit. Azure keys / WeChat AppSecret are injected via the UGREEN Docker compose `environment` UI; `settings.py` reads them from env vars. Repo only ships `.env.example` with placeholders.

## Persistent data (mounted to NAS)

The container is disposable; anything that must survive a rebuild is mounted to the NAS:

| Data | Container path | NAS path |
|------|----------------|----------|
| Raw images | `/app/data/uploads/medical` | `/volume1/Projects/Pika/data/uploads/medical` |
| SQLite DB | `/app/data/db` | `/volume1/Projects/Pika/data/db` |

Images are stored under `uploads/medical/{YYYY}/{MM}/` and named `{YYYYMMDD_HHMMSS}_{uuid4[:8]}.{ext}`. The DB stores **relative** image paths; absolute paths are joined with `settings.UPLOAD_DIR` at read time.

## Development

```bash
# Backend (local)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload                        # http://localhost:8000

# Test upload + parse end-to-end
curl -F file=@blood_routine.jpg http://localhost:8000/api/medical/reports
```

### Environment variables (see `.env.example`)

- `WX_APPID`, `WX_SECRET` — WeChat Mini Program credentials
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT` — Azure GPT-4.5-mini (vision)
- `DATA_DIR`, `UPLOAD_DIR`, `DB_PATH` — runtime paths (defaults wired for the container)

### NAS deployment (UGREEN Docker)

Deploy via the UGREEN Docker compose UI. Key gotcha: compose `build.context` must be `.` and all files must sit inside the shared directory the UGREEN UI creates. Inject secrets through the compose `environment` fields.

## Scope notes

- **Current scope = LAN POC**: WeChat dev-tool / developer's own phone preview connecting to the NAS LAN IP. Dev versions can hit `http://<lan-ip>:8000` by ticking "do not verify legal domain" in WeChat DevTools.
- **Public HTTPS domain** (for family to use anywhere via experience/production version) is a **later phase**, not implemented yet.
