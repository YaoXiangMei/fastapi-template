"""患者 API 路由。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.core.schemas import RefreshRequest, TokenResponse
from app.modules.patient import service
from app.modules.patient.deps import get_current_patient
from app.modules.patient.models import Patient
from app.modules.patient.schemas import PatientCreate, PatientRead

router = APIRouter()


@router.post("/register", response_model=ApiResponse[PatientRead], status_code=201)
async def register(data: PatientCreate, db: AsyncSession = Depends(get_db)):
    """患者注册。"""
    patient = await service.register(db, data)
    return {"status": 1, "message": "success", "data": PatientRead.model_validate(patient)}


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """患者登录，返回 JWT token。"""
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


@router.get("/me", response_model=ApiResponse[PatientRead])
async def get_me(current_patient: Patient = Depends(get_current_patient)):
    """获取当前登录患者的信息。"""
    return {"status": 1, "message": "success", "data": PatientRead.model_validate(current_patient)}
