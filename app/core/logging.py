"""使用 loguru 的结构化日志配置。"""

import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """配置 loguru 日志记录器，使用 JSON 或文本格式。"""
    logger.remove()

    if settings.LOG_JSON_FORMAT or settings.is_prod:
        # 容器/生产环境使用 JSON 格式
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL,
            serialize=True,
            backtrace=False,
            diagnose=False,
        )
    else:
        # 开发环境使用美观的文本格式
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<yellow>{extra[request_id]}</yellow> - "
                "{message}"
            ),
            backtrace=True,
            diagnose=True,
        )

    logger.info("Logging configured | env={} json={}", settings.ENV, settings.LOG_JSON_FORMAT)


logger = logger
