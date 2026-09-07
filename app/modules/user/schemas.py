"""用户与 RBAC 的 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


# ── 权限 ──
class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None = None


# ── 角色 ──
class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None = None
    permissions: list[PermissionRead] = []


class RoleCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    permission_ids: list[UUID] = []


# ── 用户 ──
class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: list[RoleRead] = []


class UserWithRoles(BaseModel):
    """用于为用户分配角色。"""

    role_ids: list[UUID]
