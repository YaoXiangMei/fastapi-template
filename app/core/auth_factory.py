"""通用认证依赖工厂。"""

from collections.abc import Callable
from typing import Type
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token


def create_auth_dependency(
    model: Type, token_url: str
) -> tuple[OAuth2PasswordBearer, Callable]:
    """为特定角色创建 OAuth2 认证依赖。

    Args:
        model: SQLAlchemy 用户模型类（Patient/Doctor/Admin）
        token_url: Swagger UI 的登录端点路径

    Returns:
        tuple: (oauth2_scheme, get_current_user_dependency)
    """
    scheme = OAuth2PasswordBearer(tokenUrl=token_url, auto_error=True)

    async def dependency(
        token: str = Depends(scheme),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            raise UnauthorizedException("Invalid or expired token")

        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token")

        try:
            user_uuid = UUID(user_id)
        except (ValueError, AttributeError):
            raise UnauthorizedException("Invalid token")

        result = await db.execute(
            select(model).where(model.id == user_uuid)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException("User not found")

        if not getattr(user, "is_active", True):
            raise UnauthorizedException("Account is disabled")

        if hasattr(user, "is_verified") and not user.is_verified:
            raise UnauthorizedException(
                "Account not verified, please wait for admin approval"
            )

        return user

    return scheme, dependency
