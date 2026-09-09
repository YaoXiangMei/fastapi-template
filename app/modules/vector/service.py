"""向量模块服务层。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.modules.vector.embeddings import generate_embedding
from app.modules.vector.models import Document
from app.modules.vector.schemas import DocumentCreate


async def create_document(db: AsyncSession, data: DocumentCreate) -> Document:
    """创建文档并自动生成其向量嵌入。"""
    embedding = generate_embedding(data.content)
    doc = Document(
        title=data.title,
        content=data.content,
        embedding=embedding,
    )
    db.add(doc)
    await db.flush()
    logger.info("Created document: {} ({})", doc.title, doc.id)
    return doc


async def get_document(db: AsyncSession, doc_id: UUID) -> Document:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundException("Document not found")
    return doc


async def list_documents(
    db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[Document], int]:
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
    )
    docs = list(result.scalars().all())

    count_result = await db.execute(select(Document))
    total = len(list(count_result.scalars().all()))
    return docs, total


async def delete_document(db: AsyncSession, doc_id: UUID) -> None:
    doc = await get_document(db, doc_id)
    await db.delete(doc)
    await db.flush()


async def search_documents(db: AsyncSession, query: str, top_k: int = 5) -> list[dict]:
    """按余弦相似度检索文档。

    返回包含 id、title、content、score（距离）的字典列表。
    score 越小表示越相似（余弦距离：0 = 完全相同，2 = 完全相反）。
    """
    query_embedding = generate_embedding(query)

    # pgvector 余弦距离运算符：'<=>'
    # 使用 select 同时查询模型和距离表达式
    stmt = (
        select(
            Document,
            Document.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(Document.embedding.isnot(None))
        .order_by("distance")
        .limit(top_k)
    )

    result = await db.execute(stmt)
    rows = result.all()

    results = []
    for doc, distance in rows:
        results.append(
            {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "score": round(1 - float(distance), 4),  # 将距离转换为相似度
            }
        )

    logger.info("Vector search for '{}' returned {} results", query, len(results))
    return results
