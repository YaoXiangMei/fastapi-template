"""通用认证依赖工厂。"""

from collections.abc import Callable as CallableType
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
    model: type,
    token_url: str,
    scheme_name: str | None = None,
    require_permissions: list[str] | None = None,
) -> tuple[OAuth2PasswordBearer, CallableType]:
    """为特定角色创建 OAuth2 认证依赖。

    Args:
        model: SQLAlchemy 用户模型类（Patient/Doctor/Admin）
        token_url: Swagger UI 的登录端点路径
        scheme_name: OpenAPI 安全方案名称（用于区分不同角色）
        require_permissions: 需要的权限码列表（仅 Admin 支持）

    Returns:
        tuple: (oauth2_scheme, get_current_user_dependency)
    """
    # 创建自定义子类以生成唯一的 OpenAPI 安全方案名称
    if scheme_name:
        scheme_class = type(
            scheme_name,
            (OAuth2PasswordBearer,),
            {"__init__": lambda self, **kwargs: OAuth2PasswordBearer.__init__(self, **kwargs)},
        )
        scheme = scheme_class(tokenUrl=token_url, auto_error=True)
    else:
        scheme = OAuth2PasswordBearer(tokenUrl=token_url, auto_error=True)

    async def dependency(
        token: str = Depends(scheme),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            payload = decode_token(token)
        except jwt.PyJWTError as err:
            raise UnauthorizedException("Invalid or expired token") from err

        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token")

        try:
            user_uuid = UUID(user_id)
        except (ValueError, AttributeError) as err:
            raise UnauthorizedException("Invalid token") from err

        result = await db.execute(select(model).where(model.id == user_uuid))  # type: ignore[var-annotated,attr-defined]
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException("User not found")

        if not getattr(user, "is_active", True):
            raise UnauthorizedException("Account is disabled")

        if hasattr(user, "is_verified") and not user.is_verified:
            raise UnauthorizedException("Account not verified, please wait for admin approval")

        # 权限检查（仅 Admin 支持）
        if (
            require_permissions
            and model.__name__ == "Admin"
            and not getattr(user, "is_superuser", False)
        ):
            from app.modules.admin.rbac_service import get_admin_permissions

            user_perms = await get_admin_permissions(db, user.id)
            if not set(require_permissions).issubset(user_perms):
                from app.core.exceptions import ForbiddenException

                raise ForbiddenException(
                    f"权限不足，需要: {', '.join(require_permissions)}"
                ) from None

        return user

    return scheme, dependency
