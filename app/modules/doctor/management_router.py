"""Admin 管理医生路由（审核、状态管理等）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.pagination import PageData, get_page_params
from app.core.response import ApiResponse
from app.modules.admin.deps import get_current_admin
from app.modules.admin.models import Admin
from app.modules.doctor.models import Doctor
from app.modules.doctor.schemas import DoctorRead

router = APIRouter(prefix="/admin/doctors", tags=["admin-doctor"])


@router.get("", response_model=ApiResponse[PageData[DoctorRead]])
async def list_doctors(
    page_params=Depends(get_page_params),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """列出所有医生（管理员）。"""
    offset = page_params.offset
    limit = page_params.limit

    result = await db.execute(
        select(Doctor).order_by(Doctor.created_at.desc()).offset(offset).limit(limit)
    )
    doctors = list(result.scalars().all())

    from sqlalchemy import func

    count_result = await db.execute(select(func.count(Doctor.id)))
    total = count_result.scalar() or 0

    return {
        "status": 1,
        "message": "success",
        "data": {
            "data": [DoctorRead.model_validate(d) for d in doctors],
            "total": total,
            "page": page_params.page,
            "page_size": page_params.page_size,
        },
    }


@router.patch("/{doctor_id}/approve", response_model=ApiResponse[DoctorRead])
async def approve_doctor(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """审核通过医生。"""
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise NotFoundException("Doctor not found")

    doctor.is_verified = True
    await db.flush()
    await db.refresh(doctor)

    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(doctor)}


@router.patch("/{doctor_id}/status", response_model=ApiResponse[DoctorRead])
async def update_doctor_status(
    doctor_id: UUID,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """启用/停用医生账号。"""
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise NotFoundException("Doctor not found")

    doctor.is_active = is_active
    await db.flush()
    await db.refresh(doctor)

    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(doctor)}
