"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.doctor.router import router as doctor_router
from app.modules.patient.router import router as patient_router
from app.modules.user.router import (
    permissions_router,
    roles_router,
    router as users_router,
)
from app.modules.vector.router import router as documents_router

api_router = APIRouter(prefix="/api/v1")

# 旧路由（保留向后兼容）
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(documents_router)

# 新多角色路由
api_router.include_router(patient_router, prefix="/patient", tags=["patient"])
api_router.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
