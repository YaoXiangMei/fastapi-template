"""患者模型。"""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class Patient(UUIDMixin, TimestampMixin, Base):
    """患者表。"""

    __tablename__ = "patients"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
