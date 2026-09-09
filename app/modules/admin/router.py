"""管理员 API 路由。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.admin import service
from app.modules.admin.deps import get_current_admin
from app.modules.admin.models import Admin
from app.modules.admin.schemas import AdminRead
from app.modules.auth.schemas import RefreshRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """管理员登录，返回 JWT token。"""
    return await service.login(db, form.username, form.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新 token。"""
    return await service.refresh(db, data.refresh_token)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """登出，吊销 refresh token。"""
    await service.logout(db, data.refresh_token)
    return {"status": 1, "message": "success", "data": None}


@router.get("/me", response_model=ApiResponse[AdminRead])
async def get_me(current_admin: Admin = Depends(get_current_admin)):
    """获取当前登录管理员的信息。"""
    return {"status": 1, "message": "success", "data": AdminRead.model_validate(current_admin)}
