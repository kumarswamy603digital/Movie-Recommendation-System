"""FastAPI application bootstrap."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

from app.api.routes.all_routes import (
    analytics_router,
    genres_router,
    movies_router,
    recs_router,
    system_router,
    users_router,
)
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.base import init_db
from app.recommender.registry import registry

configure_logging()
log = get_logger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    try:
        registry.load()
    except Exception as exc:
        log.warning("Registry load failed at startup: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("x-correlation-id") or uuid.uuid4().hex[:12]
        request.state.correlation_id = cid
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        response.headers["x-correlation-id"] = cid
        response.headers["x-process-time-ms"] = str(latency_ms)
        return response


app.add_middleware(CorrelationIdMiddleware)
register_exception_handlers(app)

api_v1 = __import__("fastapi").APIRouter(prefix="/api/v1")
api_v1.include_router(movies_router)
api_v1.include_router(genres_router)
api_v1.include_router(recs_router)
api_v1.include_router(users_router)
api_v1.include_router(analytics_router)

app.include_router(api_v1)
app.include_router(system_router, prefix="/api/v1")
# Also expose /health at the root for infrastructure probes.
app.add_api_route("/health", lambda: {"status": "ok", "version": settings.app_version}, methods=["GET"])


@app.on_event("startup")
def _preload():  # pragma: no cover
    log.info("Starting %s v%s", settings.app_name, settings.app_version)
