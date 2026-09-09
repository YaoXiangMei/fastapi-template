"""向量模块路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PageData, get_page_params
from app.core.response import ApiResponse
from app.modules.vector import service
from app.modules.vector.schemas import (
    DocumentCreate,
    DocumentRead,
    SearchRequest,
    SearchResult,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=ApiResponse[DocumentRead], status_code=201)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """创建文档。向量嵌入根据内容自动生成。"""
    doc = await service.create_document(db, data)
    return {
        "status": 1,
        "message": "success",
        "data": DocumentRead.model_validate(doc),
    }


@router.get("", response_model=ApiResponse[PageData[DocumentRead]])
async def list_documents(
    page_params=Depends(get_page_params),
    db: AsyncSession = Depends(get_db),
) -> dict:
    docs, total = await service.list_documents(db, page_params.offset, page_params.limit)
    return {
        "status": 1,
        "message": "success",
        "data": {
            "data": [DocumentRead.model_validate(d) for d in docs],
            "total": total,
            "page": page_params.page,
            "page_size": page_params.page_size,
        },
    }


@router.get("/{doc_id}", response_model=ApiResponse[DocumentRead])
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    doc = await service.get_document(db, doc_id)
    return {
        "status": 1,
        "message": "success",
        "data": DocumentRead.model_validate(doc),
    }


@router.delete("/{doc_id}", response_model=ApiResponse[None])
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await service.delete_document(db, doc_id)
    return {"status": 1, "message": "success", "data": None}


@router.post("/search", response_model=ApiResponse[list[SearchResult]])
async def search_documents(
    data: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """按语义相似度检索文档。"""
    results = await service.search_documents(db, data.query, data.top_k)
    return {
        "status": 1,
        "message": "success",
        "data": results,
    }
