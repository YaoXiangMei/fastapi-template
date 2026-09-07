"""认证路由。"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import make_rate_limiter
from app.core.response import ApiResponse
from app.modules.auth import service
from app.modules.auth.schemas import (
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.user.schemas import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[UserRead], status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """注册新用户账号。"""
    user = await service.register(
        db,
        UserCreate(email=data.email, password=data.password, full_name=data.full_name),
    )
    return {"status": 0, "message": "success", "data": UserRead.model_validate(user)}


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    dependencies=[Depends(make_rate_limiter(max_requests=5, window_seconds=60))],
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """使用邮箱 + 密码登录。返回访问令牌和刷新令牌。"""
    tokens = await service.login(db, form.username, form.password)
    return {"status": 0, "message": "success", "data": tokens}


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """轮换刷新令牌并返回新的令牌对。"""
    tokens = await service.refresh(db, data.refresh_token)
    return {"status": 0, "message": "success", "data": tokens}


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """吊销刷新令牌。"""
    await service.logout(db, data.refresh_token)
    return {"status": 0, "message": "success", "data": None}
