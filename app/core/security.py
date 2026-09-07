"""安全工具：JWT 令牌和密码哈希。"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()

# ── 密码哈希 ──────────────────────────────────


def hash_password(raw: str) -> str:
    """对明文密码进行哈希。"""
    return password_hash.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    return password_hash.verify(raw, hashed)


# ── JWT 令牌 ────────────────────────────────────────


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """创建短期的 JWT 访问令牌。

    Args:
        subject: 通常为用户 ID 字符串。
        extra_claims: 附加声明，如角色/超级用户状态。
        expires_minutes: 覆盖默认过期时间。
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_days: int | None = None,
) -> tuple[str, str]:
    """创建刷新令牌。返回 (token, jti)。

    该令牌以 jti 为键存储在 Redis 中，用于轮换/黑名单。
    """
    jti = str(uuid4())
    expire = datetime.now(timezone.utc) + timedelta(
        days=expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    """解码并验证 JWT 令牌。失败时抛出 jwt.PyJWTError。"""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
