"""使用 loguru 的结构化日志配置。"""

import sys

from loguru import logger as _original_logger

from app.core.config import settings

# Create patched logger at module level to avoid global declaration issues
if settings.LOG_JSON_FORMAT or settings.is_prod:
    # 容器/生产环境使用 JSON 格式
    _original_logger.remove()
    _original_logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        serialize=True,
        backtrace=False,
        diagnose=False,
    )
    logger = _original_logger
else:
    # 开发环境使用美观的文本格式
    _original_logger.remove()
    _original_logger.add(
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
    logger = _original_logger.patch(lambda record: record["extra"].setdefault("request_id", ""))


def setup_logging() -> None:
    """配置 loguru 日志记录器，使用 JSON 或文本格式。"""
    logger.info("Logging configured | env={} json={}", settings.ENV, settings.LOG_JSON_FORMAT)
