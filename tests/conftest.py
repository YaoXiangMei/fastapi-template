"""Pytest fixtures：测试数据库引擎/会话、fakeredis 和异步 HTTP 客户端。"""

import asyncio
import os
from typing import AsyncGenerator

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.main import app

# 导入所有模型以创建表
from app.modules.user.models import Permission, Role, User, role_permission, user_role  # noqa: F401
from app.modules.vector.models import Document  # noqa: F401
from pgvector.sqlalchemy import Vector  # noqa: F401 - 为 create_all 注册类型

# 测试数据库 URL（使用单独的测试数据库或内存数据库）
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_template_test",
)

# 为测试覆盖配置
os.environ.setdefault("ENV", "development")
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")

# 重新导入 settings 以应用测试环境
from app.core.config import Settings
from app.core import redis as redis_module
from app.core import config as config_module
config_module.settings = Settings()
from app.core import database as database_module
database_module.settings = config_module.settings

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    """为所有测试创建单个事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """测试前创建所有表，测试后删除。"""
    async with test_engine.begin() as conn:
        # 启用 pgvector 扩展
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """提供一个事务性数据库会话，每个测试后回滚。"""
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # 覆盖 get_db 依赖
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        yield session
        app.dependency_overrides.pop(get_db, None)
        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def fake_redis():
    """提供一个 fakeredis 实例并覆盖 get_redis 依赖。"""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    # 初始化全局 redis 实例
    redis_module._redis = redis

    yield redis

    # 清理
    await redis.flushall()
    redis_module._redis = None


@pytest_asyncio.fixture
async def client(db_session, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    """提供指向测试应用的异步 HTTP 客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── 辅助工具：已认证的客户端 ──────────────────────


@pytest_asyncio.fixture
async def auth_token(db_session) -> str:
    """创建一个测试用户并返回一个访问令牌。"""
    from app.core.security import create_access_token, hash_password
    from app.modules.user.models import User

    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("testpass123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"is_superuser": True},
    )
    return token


@pytest_asyncio.fixture
async def auth_client(client, auth_token) -> AsyncClient:
    """提供已认证的异步 HTTP 客户端。"""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client
