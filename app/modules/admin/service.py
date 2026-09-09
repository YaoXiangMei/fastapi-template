"""管理员业务逻辑。"""

from datetime import datetime, timezone
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.admin.models import Admin


def _refresh_key(user_id: str, jti: str) -> str:
    return f"refresh:admin:{user_id}:{jti}"


async def login(db: AsyncSession, username: str, password: str) -> dict:
    result = await db.execute(select(Admin).where(Admin.username == username))
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(password, admin.hashed_password):
        raise UnauthorizedException("Invalid username or password")
    if not admin.is_active:
        raise UnauthorizedException("Account is disabled")

    admin_id = str(admin.id)
    access_token = create_access_token(subject=admin_id)
    refresh_token, jti = create_refresh_token(admin_id)

    redis = get_redis()
    await redis.setex(
        _refresh_key(admin_id, jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    admin.last_login = datetime.now(timezone.utc)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    admin_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()

    key = _refresh_key(admin_id, jti)
    exists = await redis.get(key)
    if not exists:
        raise UnauthorizedException("Refresh token revoked or expired")

    await redis.delete(key)

    result = await db.execute(select(Admin).where(Admin.id == UUID(admin_id)))
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        raise UnauthorizedException("User not found or disabled")

    new_access = create_access_token(subject=admin_id)
    new_refresh, new_jti = create_refresh_token(admin_id)

    await redis.setex(
        _refresh_key(admin_id, new_jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(db: AsyncSession, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    admin_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(_refresh_key(admin_id, jti))
