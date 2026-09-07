"""共享的 FastAPI 依赖：数据库、Redis、当前用户、权限校验。"""

from collections.abc import Callable
from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.redis import get_redis
from app.core.security import decode_token
from app.modules.user.models import User
from app.modules.user.service import get_user_by_id, get_user_permissions

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """校验访问令牌并返回当前用户。"""
    if not token:
        raise UnauthorizedException("Not authenticated")

    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token")

    user = await get_user_by_id(db, __import__("uuid").UUID(user_id))
    if not user.is_active:
        raise UnauthorizedException("Account is disabled")

    # 将用户附加到请求状态，供下游使用
    request.state.user = user
    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求当前用户为超级用户。"""
    if not current_user.is_superuser:
        raise ForbiddenException("Superuser privileges required")
    return current_user


def require_permission(*permission_codes: str) -> Callable[..., Any]:
    """依赖工厂：要求用户拥有所有给定的权限码。

    用法::

        @router.delete(
            "/items/{id}",
            dependencies=[Depends(require_permission("items:delete"))],
        )
        async def delete_item(...): ...
    """
    required = set(permission_codes)

    async def _dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_perms = await get_user_permissions(db, current_user.id)
        if not required.issubset(user_perms):
            raise ForbiddenException(
                f"Missing permissions: {', '.join(required - user_perms)}"
            )
        return current_user

    return _dependency


# 重新导出常用依赖
__all__ = [
    "get_db",
    "get_redis",
    "get_current_user",
    "get_current_superuser",
    "require_permission",
    "oauth2_scheme",
]
