"""统一种子脚本：初始化权限、管理员账号。

用法::

    # 初始化所有数据（权限 + 管理员）
    python -m app.scripts.seed

    # 仅初始化权限
    python -m app.scripts.seed --permissions-only

    # 仅初始化管理员
    python -m app.scripts.seed --admin-only
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger, setup_logging
from app.core.security import hash_password
from app.modules.admin.models import Admin, AdminPermission

# 预定义权限
PERMISSIONS = [
    # 医生管理
    ("doctor:view", "查看医生", "查看医生列表和详情"),
    ("doctor:approve", "审核医生", "审核新注册的医生"),
    ("doctor:delete", "删除医生", "删除医生账号"),
    # 患者管理
    ("patient:view", "查看患者", "查看患者列表和详情"),
    ("patient:delete", "删除患者", "删除患者账号"),
    # 管理员管理
    ("admin:create", "创建管理员", "创建新的管理员账号"),
    ("admin:delete", "删除管理员", "删除管理员账号"),
    # 角色权限管理
    ("role:manage", "管理角色", "创建、编辑、删除角色"),
    # 系统
    ("system:config", "系统配置", "修改系统配置"),
    ("report:view", "查看报表", "查看系统报表"),
    ("data:export", "导出数据", "导出系统数据"),
]


async def seed_permissions() -> None:
    """创建预定义权限。"""
    async with async_session_factory() as db:
        for code, name, description in PERMISSIONS:
            result = await db.execute(select(AdminPermission).where(AdminPermission.code == code))
            existing = result.scalar_one_or_none()
            if existing:
                logger.info("Permission already exists: {}", code)
                continue
            perm = AdminPermission(code=code, name=name, description=description)
            db.add(perm)
            logger.info("Created permission: {} - {}", code, name)
        await db.commit()
        logger.info("Permission seeding completed")


async def seed_admin() -> None:
    """创建初始管理员账号。"""
    async with async_session_factory() as db:
        username = settings.SUPERUSER_EMAIL.split("@")[0] if settings.SUPERUSER_EMAIL else "admin"
        password = settings.SUPERUSER_PASSWORD or "admin123456"
        email = settings.SUPERUSER_EMAIL or "admin@example.com"

        result = await db.execute(select(Admin).where(Admin.username == username))
        existing = result.scalar_one_or_none()
        if existing:
            logger.info("Admin account already exists: {}", username)
            return

        admin = Admin(
            username=username,
            hashed_password=hash_password(password),
            full_name="System Admin",
            email=email,
            is_superuser=True,
        )
        db.add(admin)
        await db.commit()
        logger.info("Created admin account: {} ({})", username, email)


async def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Seed initial data")
    parser.add_argument("--permissions-only", action="store_true", help="Only seed permissions")
    parser.add_argument("--admin-only", action="store_true", help="Only seed admin")
    args = parser.parse_args()

    logger.info("Starting seed script...")

    if args.permissions_only:
        await seed_permissions()
    elif args.admin_only:
        await seed_admin()
    else:
        await seed_permissions()
        await seed_admin()

    logger.info("Seed script completed!")


if __name__ == "__main__":
    asyncio.run(main())
