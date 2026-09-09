"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.modules.admin.rbac_router import router as admin_rbac_router
from app.modules.admin.router import router as admin_router
from app.modules.doctor.management_router import router as doctor_management_router
from app.modules.doctor.router import router as doctor_router
from app.modules.patient.router import router as patient_router
from app.modules.vector.router import router as documents_router

api_router = APIRouter(prefix="/api/v1")

# 多角色路由
api_router.include_router(patient_router, prefix="/patient", tags=["patient"])
api_router.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

# Admin RBAC 管理路由
api_router.include_router(admin_rbac_router)

# Admin 医生管理路由
api_router.include_router(doctor_management_router)

# 其他路由
api_router.include_router(documents_router)
