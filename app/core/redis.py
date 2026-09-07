"""Redis 异步连接池。"""

from redis.asyncio import Redis, from_url

from app.core.config import settings

_redis: Redis | None = None


async def init_redis() -> Redis:
    """初始化 Redis 连接池。在应用生命周期启动时调用。"""
    global _redis
    _redis = from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=20,
    )
    return _redis


async def close_redis() -> None:
    """关闭 Redis 连接池。在应用生命周期关闭时调用。"""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis:
    """返回当前 Redis 实例。

    如果 Redis 尚未初始化，则抛出 RuntimeError。
    """
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis
