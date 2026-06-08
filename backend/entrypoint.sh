#!/bin/sh
set -e

# One-time transition: a pre-Alembic DB has the tables but no alembic_version.
# Stamp it to the initial revision so `upgrade head` applies only newer migrations
# instead of trying to recreate existing tables. Idempotent across deploys.
python - <<'PY'
import sqlite3, os
db = os.environ.get("DB_PATH", "/app/data/db/pika.db")
INITIAL = "0b1699f23be3"
need_stamp = False
if os.path.exists(db):
    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    if "medical_reports" in names and "alembic_version" not in names:
        need_stamp = True
    con.close()
if need_stamp:
    print("[entrypoint] pre-Alembic DB detected -> stamping initial revision")
    os.system(f"alembic stamp {INITIAL}")
PY

echo "[entrypoint] running alembic upgrade head"
alembic upgrade head

echo "[entrypoint] starting uvicorn"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
