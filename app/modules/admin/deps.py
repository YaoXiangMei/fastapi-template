"""管理员端认证依赖。"""

from app.core.auth_factory import create_auth_dependency
from app.modules.admin.models import Admin

oauth2_scheme, get_current_admin = create_auth_dependency(
    Admin,
    token_url="/api/v1/admin/login",
    scheme_name="AdminAuth",
)

__all__ = ["oauth2_scheme", "get_current_admin"]
