"""健康检查测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 1
    assert body["data"]["status"] == "alive"


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 1
    assert body["data"]["name"] == "FastAPI Template"


@pytest.mark.asyncio
async def test_unified_response_format(client: AsyncClient):
    """验证所有响应遵循 {status, message, data} 格式。"""
    resp = await client.get("/health/live")
    body = resp.json()
    assert "status" in body
    assert "message" in body
    assert "data" in body
