"""向量模块模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    title: str
    content: str


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class SearchResult(BaseModel):
    """单个检索结果项。"""

    id: UUID
    title: str
    content: str
    score: float


class SearchRequest(BaseModel):
    """相似度检索请求。"""

    query: str
    top_k: int = 5
