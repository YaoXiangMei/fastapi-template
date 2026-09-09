"""医生 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class DoctorCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    phone: str | None = None
    license_no: str
    specialty: str | None = None
    department: str | None = None
    title: str | None = None


class DoctorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    phone: str | None = None
    license_no: str
    specialty: str | None = None
    department: str | None = None
    title: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class DoctorUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    specialty: str | None = None
    department: str | None = None
    title: str | None = None
