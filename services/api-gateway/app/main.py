"""FastAPI application factory and wiring."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .adapters import build_queue
from .api.v1 import api_router, ops_router
from .config import Settings, get_settings
from .core.db import configure_db, dispose_db
from .core.observability import ObservabilityMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis.gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = getattr(app.state, "settings", None) or get_settings()

    if settings.database_url:
        configure_db(settings.database_url)
    else:
        logger.warning("DATABASE_URL not set; DB-backed endpoints will 503")

    app.state.queue = build_queue(settings)

    app.state.redis = None
    if settings.redis_url:
        try:
            import redis.asyncio as aioredis

            app.state.redis = aioredis.from_url(settings.redis_url)
            if settings.rate_limit_backend == "redis":
                from .core.rate_limit import RedisRateLimiter

                app.state.rate_limiter = RedisRateLimiter(app.state.redis)
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis init failed: %s", exc)

    yield

    if app.state.redis is not None:
        try:
            await app.state.redis.aclose()
        except Exception:  # pragma: no cover
            pass
    await dispose_db()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        description="Multi-agent AI investment research platform.",
    )
    app.state.settings = settings

    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ops_router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
