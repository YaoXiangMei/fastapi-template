"""初始管理员种子脚本。

用法：
    python -m app.scripts.seed_admin
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger
from app.core.security import hash_password
from app.modules.admin.models import Admin


async def seed_admin():
    """创建初始管理员账号。"""
    async with async_session_factory() as db:
        username = settings.SUPERUSER_EMAIL.split("@")[0] if settings.SUPERUSER_EMAIL else "admin"
        password = settings.SUPERUSER_PASSWORD or "admin123456"
        email = settings.SUPERUSER_EMAIL or "admin@example.com"

        # 检查是否已存在
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
        )
        db.add(admin)
        await db.commit()

        logger.info("Created admin account: {} ({})", username, email)


if __name__ == "__main__":
    asyncio.run(seed_admin())
