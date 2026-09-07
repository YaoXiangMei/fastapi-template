"""认证模型。"""

from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    """访问令牌 + 刷新令牌响应。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 访问令牌过期前的秒数


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class MessageResponse(BaseModel):
    message: str
