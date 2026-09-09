"""管理员模块测试。"""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.admin.models import Admin


class TestAdminLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db_session):
        admin = Admin(
            username="admin",
            hashed_password=hash_password("admin123456"),
            full_name="Test Admin",
            email="admin@test.com",
        )
        db_session.add(admin)
        await db_session.flush()

        response = await client.post(
            "/api/v1/admin/login",
            data={"username": "admin", "password": "admin123456"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(self, client: AsyncClient, db_session):
        admin = Admin(
            username="admin2",
            hashed_password=hash_password("admin123456"),
            full_name="Test Admin",
        )
        db_session.add(admin)
        await db_session.flush()

        response = await client.post(
            "/api/v1/admin/login",
            data={"username": "admin2", "password": "wrongpassword"},
        )
        assert response.status_code == 401
