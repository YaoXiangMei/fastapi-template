"""基于 Redis 的固定窗口限流器，作为 FastAPI 依赖。"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request

from app.core.config import settings
from app.core.exceptions import RateLimitException
from app.core.logging import logger
from app.core.redis import get_redis


async def rate_limit(
    request: Request,
    redis=Depends(get_redis),
    *,
    key_prefix: str = "rl",
    max_requests: int = 60,
    window_seconds: int = 60,
) -> None:
    """固定窗口限流器。

    Args:
        key_prefix: Redis 键前缀。
        max_requests: 窗口内允许的最大请求数。
        window_seconds: 窗口时长（秒）。
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    client_ip = request.client.host if request.client else "unknown"
    route = request.url.path
    cache_key = f"{key_prefix}:{route}:{client_ip}"

    try:
        current = await redis.incr(cache_key)
        if current == 1:
            await redis.expire(cache_key, window_seconds)

        if current > max_requests:
            logger.warning("Rate limit exceeded for {} on {}", client_ip, route)
            raise RateLimitException(
                f"Too many requests. Limit: {max_requests} per {window_seconds}s"
            )
    except RateLimitException:
        raise
    except Exception as e:
        logger.error("Rate limit check failed: {}", e)
        # 失败放行：Redis 不可用时允许请求通过
        return


def make_rate_limiter(
    max_requests: int = 60,
    window_seconds: int = 60,
    key_prefix: str = "rl",
) -> Callable[..., Any]:
    """创建自定义参数的限流依赖。

    用法::

        @router.post(
            "/login",
            dependencies=[Depends(make_rate_limiter(max_requests=5, window_seconds=60))],
        )
        async def login(...):
            ...
    """

    async def _dependency(
        request: Request,
        redis=Depends(get_redis),
    ) -> None:
        await rate_limit(
            request,
            redis,
            key_prefix=key_prefix,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return _dependency
