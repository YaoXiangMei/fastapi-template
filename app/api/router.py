"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.user.router import (
    permissions_router,
    roles_router,
    router as users_router,
)
from app.modules.vector.router import router as documents_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(documents_router)
