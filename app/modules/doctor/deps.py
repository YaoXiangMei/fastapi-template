"""医生端认证依赖。"""

from app.core.auth_factory import create_auth_dependency
from app.modules.doctor.models import Doctor

oauth2_scheme, get_current_doctor = create_auth_dependency(
    Doctor,
    token_url="/api/v1/doctor/login",
    scheme_name="DoctorAuth",
)

__all__ = ["oauth2_scheme", "get_current_doctor"]
