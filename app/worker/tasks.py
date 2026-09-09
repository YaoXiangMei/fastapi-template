"""Celery 任务定义。"""

import asyncio
from datetime import UTC

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.demo_task")
def demo_task(message: str) -> str:
    """一个简单的演示任务。"""
    print(f"[Celery Task] demo_task: {message}")
    return f"Processed: {message}"


@celery_app.task(name="app.worker.tasks.send_email")
def send_email(to: str, subject: str, body: str) -> dict:
    """模拟发送邮件。替换为真实的邮件服务。"""
    print(f"[Celery Task] Sending email to {to}: {subject}")
    # 生产环境中，集成真实的邮件服务商（如 SMTP、SendGrid）
    return {"to": to, "subject": subject, "status": "sent"}


@celery_app.task(name="app.worker.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> str:
    """定时任务：清理过期的 Redis 刷新令牌。

    Redis 会自动处理 TTL，但此任务可做额外清理
    （如孤儿键、审计日志）。
    """
    from app.core.redis import get_redis

    async def _cleanup():
        redis = get_redis()
        # 扫描 refresh_token:* 键
        count = 0
        async for key in redis.scan_iter(match="refresh_token:*"):
            ttl = await redis.ttl(key)
            if ttl == -2:  # 键不存在（已过期）
                count += 1
        return f"Cleaned up {count} expired tokens"

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_cleanup())
    finally:
        loop.close()
    print(f"[Celery Task] {result}")
    return result


@celery_app.task(name="app.worker.tasks.health_check")
def health_check() -> str:
    """用于监控的简单心跳任务。"""
    from datetime import datetime

    ts = datetime.now(UTC).isoformat()
    print(f"[Celery Task] Health check at {ts}")
    return ts


@celery_app.task(name="app.worker.tasks.process_document_embedding")
def process_document_embedding(document_id: str, content: str) -> dict:
    """异步生成并存储文档的嵌入向量。"""
    from app.modules.vector.embeddings import generate_embedding

    embedding = generate_embedding(content)
    print(f"[Celery Task] Generated embedding for document {document_id} (dim={len(embedding)})")
    # 生产环境中：用嵌入向量更新数据库中的文档
    return {"document_id": document_id, "embedding_dim": len(embedding)}
