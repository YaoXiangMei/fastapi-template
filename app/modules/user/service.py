"""用户、角色、权限服务层。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password
from app.core.logging import logger
from app.modules.user.models import Permission, Role, User
from app.modules.user.schemas import (
    RoleCreate,
    UserCreate,
    UserUpdate,
)


# ── 用户 CRUD ──────────────────────────────────────────


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    return user


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise ConflictException("Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, attribute_names=["roles"])
    logger.info("Created user: {} ({})", user.email, user.id)
    return user


async def update_user(db: AsyncSession, user_id: UUID, data: UserUpdate) -> User:
    user = await get_user_by_id(db, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user, attribute_names=["roles", "updated_at"])
    return user


async def list_users(
    db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[User], int]:
    result = await db.execute(select(User).offset(offset).limit(limit))
    users = list(result.scalars().all())
    count_result = await db.execute(select(User))
    total = len(list(count_result.scalars().all()))
    return users, total


async def assign_roles(db: AsyncSession, user_id: UUID, role_ids: list[UUID]) -> User:
    user = await get_user_by_id(db, user_id)
    result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    roles = list(result.scalars().all())
    if len(roles) != len(role_ids):
        raise NotFoundException("One or more roles not found")
    user.roles = roles
    await db.flush()
    return user


# ── 角色 CRUD ──────────────────────────────────────────


async def list_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(select(Role))
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: UUID) -> Role:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundException("Role not found")
    return role


async def create_role(db: AsyncSession, data: RoleCreate) -> Role:
    # 检查角色 code 是否已存在
    result = await db.execute(select(Role).where(Role.code == data.code))
    if result.scalar_one_or_none():
        raise ConflictException(f"Role code '{data.code}' already exists")

    role = Role(
        code=data.code,
        name=data.name,
        description=data.description,
    )
    db.add(role)
    await db.flush()

    if data.permission_ids:
        perm_result = await db.execute(
            select(Permission).where(Permission.id.in_(data.permission_ids))
        )
        role.permissions = list(perm_result.scalars().all())

    logger.info("Created role: {} ({})", role.code, role.id)
    return role


async def delete_role(db: AsyncSession, role_id: UUID) -> None:
    role = await get_role(db, role_id)
    await db.delete(role)
    await db.flush()


# ── 权限 CRUD ────────────────────────────────────


async def list_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission))
    return list(result.scalars().all())


async def create_permission(
    db: AsyncSession, code: str, name: str, description: str | None = None
) -> Permission:
    result = await db.execute(select(Permission).where(Permission.code == code))
    if result.scalar_one_or_none():
        raise ConflictException(f"Permission code '{code}' already exists")

    perm = Permission(code=code, name=name, description=description)
    db.add(perm)
    await db.flush()
    return perm


async def get_user_permissions(db: AsyncSession, user_id: UUID) -> set[str]:
    """返回用户的权限码集合。"""
    user = await get_user_by_id(db, user_id)
    codes: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            codes.add(perm.code)
    return codes
