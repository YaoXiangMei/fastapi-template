"""患者业务逻辑。"""

from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.patient.models import Patient
from app.modules.patient.schemas import PatientCreate


def _refresh_key(user_id: str, jti: str) -> str:
    """患者 refresh token 的 Redis 键。"""
    return f"refresh:patient:{user_id}:{jti}"


async def register(db: AsyncSession, data: PatientCreate) -> Patient:
    """注册新患者。"""
    existing = await db.execute(select(Patient).where(Patient.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictException("Email already registered")

    patient = Patient(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        gender=data.gender,
        birth_date=data.birth_date,
    )
    db.add(patient)
    await db.flush()
    await db.refresh(patient)
    return patient


async def login(db: AsyncSession, email: str, password: str) -> dict:
    """患者登录，返回 token 对。"""
    result = await db.execute(select(Patient).where(Patient.email == email))
    patient = result.scalar_one_or_none()

    if not patient or not verify_password(password, patient.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not patient.is_active:
        raise UnauthorizedException("Account is disabled")

    patient_id = str(patient.id)
    access_token = create_access_token(subject=patient_id)
    refresh_token, jti = create_refresh_token(patient_id)

    redis = get_redis()
    await redis.setex(
        _refresh_key(patient_id, jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    """刷新 token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as err:
        raise UnauthorizedException("Invalid refresh token") from err

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    patient_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()

    key = _refresh_key(patient_id, jti)
    exists = await redis.get(key)
    if not exists:
        raise UnauthorizedException("Refresh token revoked or expired")

    await redis.delete(key)

    result = await db.execute(select(Patient).where(Patient.id == UUID(patient_id)))
    patient = result.scalar_one_or_none()
    if not patient or not patient.is_active:
        raise UnauthorizedException("User not found or disabled")

    new_access = create_access_token(subject=patient_id)
    new_refresh, new_jti = create_refresh_token(patient_id)

    await redis.setex(
        _refresh_key(patient_id, new_jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(db: AsyncSession, refresh_token: str) -> None:
    """登出，吊销 refresh token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as err:
        raise UnauthorizedException("Invalid refresh token") from err

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    patient_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(_refresh_key(patient_id, jti))
