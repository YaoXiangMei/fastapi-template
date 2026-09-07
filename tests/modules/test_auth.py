"""认证流程测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "full_name": "New User",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == 0
    assert body["data"]["email"] == "newuser@example.com"
    assert body["data"]["is_active"] is True
    assert body["data"]["is_superuser"] is False


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session):
    from app.core.security import hash_password
    from app.modules.user.models import User

    user = User(
        email="existing@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "existing@example.com", "password": "password123"},
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["status"] == 409
    assert "already registered" in body["message"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session):
    from app.core.security import hash_password
    from app.modules.user.models import User

    user = User(
        email="login@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 0
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]
    assert body["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session):
    from app.core.security import hash_password
    from app.modules.user.models import User

    user = User(
        email="wrongpw@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrongpw@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert resp.json()["status"] == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(client: AsyncClient, auth_token):
    client.headers["Authorization"] = f"Bearer {auth_token}"
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 0
    assert body["data"]["email"] == "testuser@example.com"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db_session, fake_redis):
    from app.core.security import create_refresh_token
    from app.modules.user.models import User
    from app.core.redis import get_redis
    from app.core.config import settings

    user = User(
        email="refresh@example.com",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    refresh_token, jti = create_refresh_token(str(user.id))
    redis = get_redis()
    await redis.setex(
        f"refresh_token:{user.id}:{jti}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        "1",
    )

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


@pytest.mark.asyncio
async def test_unified_error_format(client: AsyncClient):
    """验证错误响应遵循 {status, message, data} 格式。"""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
    body = resp.json()
    assert "status" in body
    assert "message" in body
    assert body["status"] != 0
