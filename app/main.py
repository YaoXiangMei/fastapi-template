"""FastAPI 应用工厂，包含生命周期、中间件和路由注册。"""

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.core.metrics import setup_metrics
from app.core.middleware import RequestIDMiddleware
from app.core.redis import close_redis, init_redis
from app.core.response import ApiResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动与关闭生命周期。"""
    # ── 启动 ──
    setup_logging()
    logger.info("Starting application | env={}", settings.ENV)

    # 初始化 Redis
    await init_redis()
    logger.info("Redis connection initialized")

    # Sentry（可选）
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1 if settings.is_prod else 1.0,
            environment=settings.ENV,
        )
        logger.info("Sentry initialized")

    yield

    # ── 关闭 ──
    await close_redis()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title="FastAPI Template",
        description=(
            "A comprehensive FastAPI template with async SQLAlchemy, "
            "pgvector, RBAC, Celery, Redis, and more."
        ),
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=None,
    )

    # ── 中间件（顺序：最后添加的为最外层）──
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 异常处理 ──
    register_exception_handlers(app)

    # ── 路由 ──
    app.include_router(api_router)

    # ── 指标 ──
    setup_metrics(app)

    # ── 健康检查 ──
    @app.get("/health/live", response_model=ApiResponse[dict], tags=["health"])
    async def health_live() -> dict:
        """存活探针：应用进程正在运行。"""
        return {"status": 1, "message": "success", "data": {"status": "alive"}}

    @app.get("/health/ready", response_model=ApiResponse[dict], tags=["health"])
    async def health_ready() -> dict:
        """就绪探针：数据库 + Redis 连接正常。"""
        checks: dict[str, str] = {}

        # 检查数据库
        try:
            from app.core.database import async_session_factory

            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {e}"

        # 检查 Redis
        try:
            from app.core.redis import get_redis

            redis = get_redis()
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"

        all_ok = all(v == "ok" for v in checks.values())
        return {
            "status": 1 if all_ok else 0,
            "message": "ready" if all_ok else "not ready",
            "data": checks,
        }

    @app.get("/", response_model=ApiResponse[dict], tags=["root"])
    async def root() -> dict:
        """根端点，返回 API 信息。"""
        return {
            "status": 1,
            "message": "success",
            "data": {
                "name": "FastAPI Template",
                "version": "0.1.0",
                "docs": "/docs",
                "redoc": "/redoc",
                "health": "/health/ready",
            },
        }

    return app


app = create_app()
