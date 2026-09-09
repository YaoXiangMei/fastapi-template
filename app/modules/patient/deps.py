"""患者端认证依赖。"""

from app.core.auth_factory import create_auth_dependency
from app.modules.patient.models import Patient

oauth2_scheme, get_current_patient = create_auth_dependency(
    Patient,
    token_url="/api/v1/patient/login",
)

__all__ = ["oauth2_scheme", "get_current_patient"]
