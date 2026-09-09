"""管理员 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    last_login: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
