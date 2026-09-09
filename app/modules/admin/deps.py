"""管理员端认证依赖。"""

from collections.abc import Callable

from app.core.auth_factory import create_auth_dependency
from app.modules.admin.models import Admin

oauth2_scheme, get_current_admin = create_auth_dependency(
    Admin,
    token_url="/api/v1/admin/login",
    scheme_name="AdminAuth",
)


def require_admin(*permissions: str) -> Callable:
    """创建需要特定权限的认证依赖。

    用法:
        @router.delete("/doctors/{id}")
        async def delete_doctor(
            _: Admin = Depends(require_admin("doctor:delete"))
        ):
            ...
    """
    _, dependency = create_auth_dependency(
        Admin,
        token_url="/api/v1/admin/login",
        require_permissions=list(permissions),
    )
    return dependency


__all__ = ["oauth2_scheme", "get_current_admin", "require_admin"]
