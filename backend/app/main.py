import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.auth_router import router as auth_router
from app.core.exceptions import PikaException
from app.modules.medical.router import router as medical_router

logging.basicConfig(level=logging.INFO)

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


@app.get("/health")
def health():
    return {"code": 0, "msg": "ok", "data": {"service": "pika-backend"}}


app.include_router(auth_router)
app.include_router(medical_router)
