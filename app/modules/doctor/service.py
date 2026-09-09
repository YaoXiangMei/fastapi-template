"""医生业务逻辑。"""

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
from app.modules.doctor.models import Doctor
from app.modules.doctor.schemas import DoctorCreate


def _refresh_key(user_id: str, jti: str) -> str:
    return f"refresh:doctor:{user_id}:{jti}"


async def register(db: AsyncSession, data: DoctorCreate) -> Doctor:
    existing_email = await db.execute(select(Doctor).where(Doctor.email == data.email))
    if existing_email.scalar_one_or_none():
        raise ConflictException("Email already registered")

    existing_license = await db.execute(select(Doctor).where(Doctor.license_no == data.license_no))
    if existing_license.scalar_one_or_none():
        raise ConflictException("License number already registered")

    doctor = Doctor(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        license_no=data.license_no,
        specialty=data.specialty,
        department=data.department,
        title=data.title,
        is_verified=False,
    )
    db.add(doctor)
    await db.flush()
    await db.refresh(doctor)
    return doctor


async def login(db: AsyncSession, email: str, password: str) -> dict:
    result = await db.execute(select(Doctor).where(Doctor.email == email))
    doctor = result.scalar_one_or_none()

    if not doctor or not verify_password(password, doctor.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not doctor.is_active:
        raise UnauthorizedException("Account is disabled")
    if not doctor.is_verified:
        raise UnauthorizedException("Account not verified, please wait for admin approval")

    doctor_id = str(doctor.id)
    access_token = create_access_token(subject=doctor_id)
    refresh_token, jti = create_refresh_token(doctor_id)

    redis = get_redis()
    await redis.setex(
        _refresh_key(doctor_id, jti),
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
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    doctor_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()

    key = _refresh_key(doctor_id, jti)
    exists = await redis.get(key)
    if not exists:
        raise UnauthorizedException("Refresh token revoked or expired")

    await redis.delete(key)

    result = await db.execute(select(Doctor).where(Doctor.id == UUID(doctor_id)))
    doctor = result.scalar_one_or_none()
    if not doctor or not doctor.is_active:
        raise UnauthorizedException("User not found or disabled")

    new_access = create_access_token(subject=doctor_id)
    new_refresh, new_jti = create_refresh_token(doctor_id)

    await redis.setex(
        _refresh_key(doctor_id, new_jti),
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
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    doctor_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(_refresh_key(doctor_id, jti))
