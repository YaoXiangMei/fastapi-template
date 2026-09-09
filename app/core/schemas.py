"""共享认证模式。"""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """访问令牌 + 刷新令牌响应。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 访问令牌过期前的秒数


class RefreshRequest(BaseModel):
    """刷新令牌请求。"""

    refresh_token: str
