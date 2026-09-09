"""Admin 权限种子脚本。

用法：
    python -m app.scripts.seed_admin_permissions
"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import logger
from app.modules.admin.models import AdminPermission


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


async def seed_permissions():
    """创建预定义权限。"""
    async with async_session_factory() as db:
        for code, name, description in PERMISSIONS:
            # 检查是否已存在
            result = await db.execute(
                select(AdminPermission).where(AdminPermission.code == code)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info("Permission already exists: {}", code)
                continue

            perm = AdminPermission(
                code=code,
                name=name,
                description=description,
            )
            db.add(perm)
            logger.info("Created permission: {} - {}", code, name)

        await db.commit()
        logger.info("Permission seeding completed")


if __name__ == "__main__":
    asyncio.run(seed_permissions())
