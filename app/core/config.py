"""从环境变量加载的应用配置。"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── 环境 ──
    ENV: str = "development"

    @property
    def is_dev(self) -> bool:
        return self.ENV == "development"

    @property
    def is_prod(self) -> bool:
        return self.ENV == "production"

    # ── 数据库 ──
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_template"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Celery ──
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── 认证 / JWT ──
    JWT_SECRET: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── 超级用户种子 ──
    SUPERUSER_EMAIL: str = "admin@example.com"
    SUPERUSER_PASSWORD: str = "admin123456"

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            # 处理类 JSON 字符串：["a","b"] 或逗号分隔：a,b
            v = v.strip()
            if v.startswith("["):
                import json

                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── 限流 ──
    RATE_LIMIT_ENABLED: bool = True

    # ── Sentry ──
    SENTRY_DSN: str = ""

    # ── 日志 ──
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = False


@lru_cache
def get_settings() -> Settings:
    """返回缓存的配置实例。"""
    return Settings()


settings = get_settings()
