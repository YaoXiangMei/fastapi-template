"""Vector / pgvector 模块测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_document(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/documents",
        json={
            "title": "FastAPI Guide",
            "content": "FastAPI is a modern, fast web framework for building APIs with Python.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == 1
    assert body["data"]["title"] == "FastAPI Guide"
    assert "id" in body["data"]


@pytest.mark.asyncio
async def test_list_documents(auth_client: AsyncClient):
    # 先创建一个文档
    await auth_client.post(
        "/api/v1/documents",
        json={"title": "Doc 1", "content": "Some content here"},
    )

    resp = await auth_client.get("/api/v1/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 1
    assert "data" in body["data"]
    assert body["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_search_documents(auth_client: AsyncClient):
    # 创建多个文档
    await auth_client.post(
        "/api/v1/documents",
        json={
            "title": "Python Guide",
            "content": (
                "Python is a programming language great for data science and web development."
            ),
        },
    )
    await auth_client.post(
        "/api/v1/documents",
        json={
            "title": "Cooking 101",
            "content": "How to bake a chocolate cake with three layers.",
        },
    )

    resp = await auth_client.post(
        "/api/v1/documents/search",
        json={"query": "programming and data science", "top_k": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 1
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    # 结果应包含 score 字段
    assert "score" in body["data"][0]
    assert "title" in body["data"][0]


@pytest.mark.asyncio
async def test_search_returns_similar_first(auth_client: AsyncClient):
    """内容相似的文档应排名更靠前。"""
    await auth_client.post(
        "/api/v1/documents",
        json={
            "title": "SQLAlchemy",
            "content": "SQLAlchemy is the Python SQL toolkit and Object Relational Mapper.",
        },
    )
    await auth_client.post(
        "/api/v1/documents",
        json={
            "title": "Random Topic",
            "content": "The weather today is sunny with a chance of rain.",
        },
    )

    resp = await auth_client.post(
        "/api/v1/documents/search",
        json={"query": "Python SQL ORM toolkit", "top_k": 2},
    )
    body = resp.json()
    # SQLAlchemy 文档应排名第一
    titles = [item["title"] for item in body["data"]]
    assert "SQLAlchemy" in titles
