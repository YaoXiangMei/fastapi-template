"""医生 API 路由。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.schemas import RefreshRequest, TokenResponse
from app.modules.doctor import service
from app.modules.doctor.deps import get_current_doctor
from app.modules.doctor.models import Doctor
from app.modules.doctor.schemas import DoctorCreate, DoctorRead

router = APIRouter()


@router.post("/register", response_model=ApiResponse[DoctorRead], status_code=201)
async def register(data: DoctorCreate, db: AsyncSession = Depends(get_db)):
    """医生注册（需管理员审核后激活）。"""
    doctor = await service.register(db, data)
    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(doctor)}


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """医生登录，返回 JWT token。"""
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


@router.get("/me", response_model=ApiResponse[DoctorRead])
async def get_me(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取当前登录医生的信息。"""
    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(current_doctor)}
