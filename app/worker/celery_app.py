"""Celery 应用实例与配置。"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "fastapi_template",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # 自动发现 app.worker.tasks 中的任务
    imports=["app.worker.tasks"],
)

# ── Beat 调度（cron）───────────────────────────────
celery_app.conf.beat_schedule = {
    "daily-cleanup": {
        "task": "app.worker.tasks.cleanup_expired_tokens",
        "schedule": crontab(minute=0, hour=3),  # 每天凌晨 3 点 UTC
    },
    "health-check": {
        "task": "app.worker.tasks.health_check",
        "schedule": crontab(minute="*/5"),  # 每 5 分钟
    },
}
