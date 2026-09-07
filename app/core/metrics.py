"""Prometheus 指标设置。"""

from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app) -> None:
    """在 FastAPI 应用上注册 Prometheus 监控。"""
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_round_latency_decimals=True,
    ).instrument(app).expose(app, endpoint="/metrics")
