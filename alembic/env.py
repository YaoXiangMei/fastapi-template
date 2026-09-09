"""Alembic 环境，用于异步 SQLAlchemy。

此模块配置 Alembic 使用异步引擎，注册所有模型以支持
自动生成功能，并确保 pgvector 类型可用。
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# 导入所有模型，使其注册到 Base.metadata
from app.modules.admin.models import Admin  # noqa: F401
from app.modules.doctor.models import Doctor  # noqa: F401
from app.modules.patient.models import Patient  # noqa: F401
from app.modules.vector.models import Document  # noqa: F401

# 这是 Alembic 配置对象
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 解释配置文件以配置 Python 日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """以“离线”模式运行迁移（将 SQL 输出到 stdout）。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """以“在线”模式运行迁移，使用异步引擎。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
