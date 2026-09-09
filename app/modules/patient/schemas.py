"""患者 Pydantic 模型。"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class PatientCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    birth_date: date | None = None


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PatientUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    birth_date: date | None = None
