"""管理员 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    last_login: datetime | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


# ── 权限 ──


class PermissionCreate(BaseModel):
    code: str
    name: str
    description: str | None = None


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


# ── 角色 ──


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class RoleWithPermissions(RoleRead):
    permissions: list[PermissionRead] = []


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[UUID]


# ── Admin 角色分配 ──


class AssignRolesRequest(BaseModel):
    role_ids: list[UUID]
