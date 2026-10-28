import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from .api import router
from .config import get_settings
from .db import Base, engine
from .domain import DomainError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("returnet")
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.env in {"development", "test"}:
        Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Returnet API",
    version="0.1.0",
    description="Pilot API. ETA values are estimates, not promises.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Returnet-Dev-User"],
)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:80]
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%d request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        int((time.monotonic() - started) * 1000),
        request.state.request_id,
    )
    return response


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
    detail = cast(dict[str, Any], exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": detail["code"],
                "message": detail["message"],
                "details": detail.get("details", {}),
                "request_id": request.state.request_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http.{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
                "request_id": request.state.request_id,
            }
        },
    )


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    return {"status": "ready"}


app.include_router(router)
