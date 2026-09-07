"""用户与 RBAC 路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser, get_current_user
from app.core.database import get_db
from app.core.pagination import PageData, get_page_params
from app.core.response import ApiResponse
from app.modules.user import service
from app.modules.user.models import User
from app.modules.user.schemas import (
    PermissionRead,
    RoleCreate,
    RoleRead,
    UserCreate,
    UserRead,
    UserUpdate,
    UserWithRoles,
)

router = APIRouter(prefix="/users", tags=["users"])


# ── 当前用户 ──

@router.get("/me", response_model=ApiResponse[UserRead])
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return {"status": 1, "message": "success", "data": UserRead.model_validate(current_user)}


# ── 用户管理（仅超级用户）──

@router.get("", response_model=ApiResponse[PageData[UserRead]])
async def list_users(
    page_params=Depends(get_page_params),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    users, total = await service.list_users(db, page_params.offset, page_params.limit)
    return {
        "status": 1,
        "message": "success",
        "data": {
            "data": [UserRead.model_validate(u) for u in users],
            "total": total,
            "page": page_params.page,
            "page_size": page_params.page_size,
        },
    }


@router.post("", response_model=ApiResponse[UserRead], status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    user = await service.create_user(db, data)
    return {"status": 1, "message": "success", "data": UserRead.model_validate(user)}


@router.patch("/{user_id}", response_model=ApiResponse[UserRead])
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    user = await service.update_user(db, user_id, data)
    return {"status": 1, "message": "success", "data": UserRead.model_validate(user)}


@router.post("/{user_id}/roles", response_model=ApiResponse[UserRead])
async def assign_roles(
    user_id: UUID,
    data: UserWithRoles,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    user = await service.assign_roles(db, user_id, data.role_ids)
    return {"status": 1, "message": "success", "data": UserRead.model_validate(user)}


# ── 角色 ──

roles_router = APIRouter(prefix="/roles", tags=["roles"])


@roles_router.get("", response_model=ApiResponse[list[RoleRead]])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    roles = await service.list_roles(db)
    return {
        "status": 1,
        "message": "success",
        "data": [RoleRead.model_validate(r) for r in roles],
    }


@roles_router.post("", response_model=ApiResponse[RoleRead], status_code=201)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    role = await service.create_role(db, data)
    return {"status": 1, "message": "success", "data": RoleRead.model_validate(role)}


@roles_router.delete("/{role_id}", response_model=ApiResponse[None])
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    await service.delete_role(db, role_id)
    return {"status": 1, "message": "success", "data": None}


# ── 权限 ──

permissions_router = APIRouter(prefix="/permissions", tags=["permissions"])


@permissions_router.get("", response_model=ApiResponse[list[PermissionRead]])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    perms = await service.list_permissions(db)
    return {
        "status": 1,
        "message": "success",
        "data": [PermissionRead.model_validate(p) for p in perms],
    }
