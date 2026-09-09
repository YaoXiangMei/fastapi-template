"""Admin RBAC 管理路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.admin import rbac_service
from app.modules.admin.deps import get_current_admin
from app.modules.admin.models import Admin
from app.modules.admin.schemas import (
    AssignPermissionsRequest,
    AssignRolesRequest,
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RoleRead,
    RoleWithPermissions,
)

router = APIRouter(prefix="/admin", tags=["admin-rbac"])


# ── 权限管理 ──


@router.post("/permissions", response_model=ApiResponse[PermissionRead], status_code=201)
async def create_permission(
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """创建权限。需要超级管理员权限。"""
    if not current_admin.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("需要超级管理员权限")

    perm = await rbac_service.create_permission(db, data)
    return {"status": 1, "message": "success", "data": PermissionRead.model_validate(perm)}


@router.get("/permissions", response_model=ApiResponse[list[PermissionRead]])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """列出所有权限。"""
    perms = await rbac_service.list_permissions(db)
    return {"status": 1, "message": "success", "data": [PermissionRead.model_validate(p) for p in perms]}


# ── 角色管理 ──


@router.post("/roles", response_model=ApiResponse[RoleRead], status_code=201)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """创建角色。需要超级管理员权限。"""
    if not current_admin.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("需要超级管理员权限")

    role = await rbac_service.create_role(db, data)
    return {"status": 1, "message": "success", "data": RoleRead.model_validate(role)}


@router.get("/roles", response_model=ApiResponse[list[RoleRead]])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """列出所有角色。"""
    roles = await rbac_service.list_roles(db)
    return {"status": 1, "message": "success", "data": [RoleRead.model_validate(r) for r in roles]}


@router.post("/roles/{role_id}/permissions", response_model=ApiResponse[RoleWithPermissions])
async def assign_permissions(
    role_id: UUID,
    data: AssignPermissionsRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """给角色分配权限。需要超级管理员权限。"""
    if not current_admin.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("需要超级管理员权限")

    role = await rbac_service.assign_permissions_to_role(db, role_id, data.permission_ids)
    return {"status": 1, "message": "success", "data": RoleWithPermissions.model_validate(role)}


# ── Admin 角色分配 ──


@router.get("/users", response_model=ApiResponse[list[dict]])
async def list_admins(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """列出所有管理员。需要超级管理员权限。"""
    if not current_admin.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("需要超级管理员权限")

    result = await db.execute(select(Admin))
    admins = result.scalars().all()
    return {
        "status": 1,
        "message": "success",
        "data": [
            {
                "id": str(a.id),
                "username": a.username,
                "full_name": a.full_name,
                "email": a.email,
                "is_superuser": a.is_superuser,
                "roles": [{"id": str(r.id), "name": r.name} for r in a.roles],
            }
            for a in admins
        ],
    }


@router.post("/users/{admin_id}/roles", response_model=ApiResponse[dict])
async def assign_roles(
    admin_id: UUID,
    data: AssignRolesRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """给管理员分配角色。需要超级管理员权限。"""
    if not current_admin.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("需要超级管理员权限")

    admin = await rbac_service.assign_roles_to_admin(db, admin_id, data.role_ids)
    return {
        "status": 1,
        "message": "success",
        "data": {
            "id": str(admin.id),
            "username": admin.username,
            "roles": [{"id": str(r.id), "name": r.name} for r in admin.roles],
        },
    }
