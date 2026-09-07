"""种子脚本：创建默认权限、角色和超级用户。

用法::

    python -m app.scripts.seed
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger, setup_logging
from app.core.security import hash_password
from app.modules.user.models import Permission, Role, User
from app.modules.user.service import get_user_by_email


DEFAULT_PERMISSIONS = [
    ("users:read", "Read Users", "查看用户列表和详情"),
    ("users:write", "Write Users", "创建、更新或删除用户"),
    ("users:delete", "Delete Users", "删除用户"),
    ("roles:manage", "Manage Roles", "创建、更新、删除角色并分配权限"),
    ("documents:read", "Read Documents", "查看文档"),
    ("documents:write", "Write Documents", "创建、更新或删除文档"),
    ("documents:search", "Search Documents", "按相似度搜索文档"),
]


async def seed_permissions(db) -> None:
    for code, name, desc in DEFAULT_PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.code == code))
        if result.scalar_one_or_none():
            continue
        perm = Permission(code=code, name=name, description=desc)
        db.add(perm)
        await db.flush()
        logger.info("Created permission: {}", code)
    await db.commit()


async def seed_roles(db) -> None:
    # 获取所有权限
    result = await db.execute(select(Permission))
    all_perms = list(result.scalars().all())

    # 管理员角色：拥有所有权限
    result = await db.execute(select(Role).where(Role.code == "admin"))
    admin_role = result.scalar_one_or_none()
    if not admin_role:
        admin_role = Role(
            code="admin",
            name="Administrator",
            description="Full system access",
        )
        db.add(admin_role)
        await db.flush()
        logger.info("Created role: admin")
    admin_role.permissions = all_perms

    # 用户角色：只读权限
    result = await db.execute(select(Role).where(Role.code == "user"))
    user_role = result.scalar_one_or_none()
    if not user_role:
        user_role = Role(
            code="user",
            name="Standard User",
            description="Basic read access",
        )
        db.add(user_role)
        await db.flush()
        logger.info("Created role: user")

    read_perms = [p for p in all_perms if p.code.endswith(":read") or p.code.endswith(":search")]
    user_role.permissions = read_perms

    await db.commit()


async def seed_superuser(db) -> None:
    existing = await get_user_by_email(db, settings.SUPERUSER_EMAIL)
    if existing:
        logger.info("Superuser already exists: {}", settings.SUPERUSER_EMAIL)
        return

    result = await db.execute(select(Role).where(Role.code == "admin"))
    admin_role = result.scalar_one_or_none()

    user = User(
        email=settings.SUPERUSER_EMAIL,
        hashed_password=hash_password(settings.SUPERUSER_PASSWORD),
        is_active=True,
        is_superuser=True,
        full_name="Super Admin",
    )
    if admin_role:
        user.roles = [admin_role]
    db.add(user)
    await db.commit()
    logger.info("Created superuser: {}", settings.SUPERUSER_EMAIL)


async def main() -> None:
    setup_logging()
    logger.info("Starting seed script...")
    async with async_session_factory() as db:
        await seed_permissions(db)
        await seed_roles(db)
        await seed_superuser(db)
    logger.info("Seed script completed!")


if __name__ == "__main__":
    asyncio.run(main())
