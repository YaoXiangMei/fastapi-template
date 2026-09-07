"""用户管理测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users_as_superuser(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 0
    assert "items" in body["data"]
    assert "total" in body["data"]
    assert "page" in body["data"]
    assert "page_size" in body["data"]


@pytest.mark.asyncio
async def test_create_user_as_superuser(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/users",
        json={
            "email": "managed@example.com",
            "password": "StrongPass123",
            "full_name": "Managed User",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == 0
    assert body["data"]["email"] == "managed@example.com"


@pytest.mark.asyncio
async def test_update_user(auth_client: AsyncClient):
    # 先创建用户
    create_resp = await auth_client.post(
        "/api/v1/users",
        json={"email": "update@example.com", "password": "StrongPass123"},
    )
    user_id = create_resp.json()["data"]["id"]

    resp = await auth_client.patch(
        f"/api/v1/users/{user_id}",
        json={"full_name": "Updated Name", "is_active": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["full_name"] == "Updated Name"
    assert body["data"]["is_active"] is False


@pytest.mark.asyncio
async def test_list_roles(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/roles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 0
    assert isinstance(body["data"], list)
