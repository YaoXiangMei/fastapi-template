"""带有 pgvector 向量列的文档模型。"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.vector.embeddings import EMBEDDING_DIM


class Document(UUIDMixin, TimestampMixin, Base):
    """带有向量嵌入的文本文档，用于相似度检索。"""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
