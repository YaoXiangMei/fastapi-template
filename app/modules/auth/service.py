"""认证服务：注册、登录、刷新、登出。"""

from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.logging import logger
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.user.models import User
from app.modules.user.schemas import UserCreate
from app.modules.user.service import create_user, get_user_by_email


def _refresh_key(user_id: str, jti: str) -> str:
    """刷新令牌的 Redis 键。"""
    return f"refresh_token:{user_id}:{jti}"


async def register(db, data: UserCreate) -> User:
    """注册新用户。"""
    user = await create_user(db, data)
    return user


async def login(db, email: str, password: str) -> dict:
    """认证用户并返回令牌对。"""
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedException("Account is disabled")

    user_id = str(user.id)
    access_token = create_access_token(
        subject=user_id,
        extra_claims={"is_superuser": user.is_superuser},
    )
    refresh_token, jti = create_refresh_token(user_id)

    # 将刷新令牌的 jti 存入 Redis
    redis = get_redis()
    await redis.setex(
        _refresh_key(user_id, jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        "1",
    )

    logger.info("User logged in: {} ({})", user.email, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh(db, refresh_token: str) -> dict:
    """轮换刷新令牌并返回新的令牌对。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    user_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()

    # 校验刷新令牌是否存在于 Redis（未被吊销）
    key = _refresh_key(user_id, jti)
    exists = await redis.get(key)
    if not exists:
        raise UnauthorizedException("Refresh token revoked or expired")

    # 删除旧的 jti（轮换）
    await redis.delete(key)

    # 签发新令牌
    # 获取用户信息用于附加声明
    from app.modules.user.service import get_user_by_id
    from uuid import UUID

    user = await get_user_by_id(db, UUID(user_id))

    new_access = create_access_token(
        subject=user_id,
        extra_claims={"is_superuser": user.is_superuser},
    )
    new_refresh, new_jti = create_refresh_token(user_id)

    await redis.setex(
        _refresh_key(user_id, new_jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        "1",
    )

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(db, refresh_token: str) -> None:
    """吊销刷新令牌。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    user_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(_refresh_key(user_id, jti))

    logger.info("User logged out: {}", user_id)
