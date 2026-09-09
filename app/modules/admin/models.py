"""管理员 RBAC 模型。"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin


class Admin(UUIDMixin, TimestampMixin, Base):
    """管理员表。"""

    __tablename__ = "admins"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 多对多关系：Admin → Roles
    roles = relationship(
        "AdminRole",
        secondary="admin_role_assignments",
        back_populates="admins",
        lazy="selectin",
    )


class AdminRole(UUIDMixin, TimestampMixin, Base):
    """管理员角色。"""

    __tablename__ = "admin_roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 多对多关系：Role → Permissions
    permissions = relationship(
        "AdminPermission",
        secondary="admin_role_permissions",
        back_populates="roles",
        lazy="selectin",
    )

    # 反向关系
    admins = relationship(
        "Admin",
        secondary="admin_role_assignments",
        back_populates="roles",
    )


class AdminPermission(UUIDMixin, TimestampMixin, Base):
    """管理员权限。"""

    __tablename__ = "admin_permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 反向关系
    roles = relationship(
        "AdminRole",
        secondary="admin_role_permissions",
        back_populates="permissions",
    )


# 关联表
admin_role_assignments = Table(
    "admin_role_assignments",
    Base.metadata,
    Column(
        "admin_id",
        UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("admin_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

admin_role_permissions = Table(
    "admin_role_permissions",
    Base.metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("admin_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("admin_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
