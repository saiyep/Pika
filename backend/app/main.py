import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.auth_router import router as auth_router
from app.core.db import engine
from app.core.exceptions import PikaException
from app.modules.medical.router import router as medical_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# httpx logs the full request URL at INFO — for the WeChat jscode2session call
# that URL contains appid+secret. Silence it so credentials never hit the logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Bump on each deploy so /health proves which build is actually running.
APP_VERSION = "0.2.0"

app = FastAPI(title="Pika Family Service Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # POC: WeChat Mini Program / dev tools
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PikaException)
def handle_pika_exception(request: Request, exc: PikaException):
    return JSONResponse(
        status_code=200,
        content={"code": exc.code, "msg": exc.msg, "data": None},
    )


def _db_revision() -> str | None:
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            return row[0] if row else None
    except Exception:
        return None


@app.get("/health")
def health():
    return {
        "code": 0,
        "msg": "ok",
        "data": {
            "service": "pika-backend",
            "version": APP_VERSION,
            "db_revision": _db_revision(),
        },
    }


app.include_router(auth_router)
app.include_router(medical_router)
