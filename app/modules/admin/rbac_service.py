"""Admin RBAC 服务层。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.modules.admin.models import Admin, AdminPermission, AdminRole
from app.modules.admin.schemas import PermissionCreate, RoleCreate


async def get_admin_permissions(db: AsyncSession, admin_id: UUID) -> set[str]:
    """获取管理员的所有权限码。"""
    result = await db.execute(
        select(Admin)
        .options(selectinload(Admin.roles).selectinload(AdminRole.permissions))
        .where(Admin.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        return set()

    permissions = set()
    for role in admin.roles:
        for perm in role.permissions:
            permissions.add(perm.code)
    return permissions


async def create_permission(
    db: AsyncSession, data: PermissionCreate
) -> AdminPermission:
    """创建权限。"""
    perm = AdminPermission(**data.model_dump())
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return perm


async def list_permissions(db: AsyncSession) -> list[AdminPermission]:
    """列出所有权限。"""
    result = await db.execute(select(AdminPermission))
    return list(result.scalars().all())


async def create_role(db: AsyncSession, data: RoleCreate) -> AdminRole:
    """创建角色。"""
    role = AdminRole(**data.model_dump())
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def list_roles(db: AsyncSession) -> list[AdminRole]:
    """列出所有角色。"""
    result = await db.execute(select(AdminRole))
    return list(result.scalars().all())


async def assign_permissions_to_role(
    db: AsyncSession, role_id: UUID, permission_ids: list[UUID]
) -> AdminRole:
    """给角色分配权限。"""
    role = await db.get(AdminRole, role_id)
    if not role:
        raise NotFoundException("角色不存在")

    perms_result = await db.execute(
        select(AdminPermission).where(AdminPermission.id.in_(permission_ids))
    )
    role.permissions = list(perms_result.scalars().all())
    await db.flush()
    await db.refresh(role)
    return role


async def assign_roles_to_admin(
    db: AsyncSession, admin_id: UUID, role_ids: list[UUID]
) -> Admin:
    """给管理员分配角色。"""
    admin = await db.get(Admin, admin_id)
    if not admin:
        raise NotFoundException("管理员不存在")

    roles_result = await db.execute(
        select(AdminRole).where(AdminRole.id.in_(role_ids))
    )
    admin.roles = list(roles_result.scalars().all())
    await db.flush()
    await db.refresh(admin)
    return admin
