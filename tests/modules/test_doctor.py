"""医生模块测试。"""

import pytest
from httpx import AsyncClient


@pytest.fixture
def doctor_data():
    return {
        "email": "doctor@test.com",
        "password": "testpassword123",
        "full_name": "Dr. Test",
        "phone": "13900139000",
        "license_no": "LIC123456",
        "specialty": "cardiology",
        "department": "内科",
        "title": "attending",
    }


class TestDoctorRegistration:
    @pytest.mark.asyncio
    async def test_register_doctor_success(self, client: AsyncClient, doctor_data):
        response = await client.post("/api/v1/doctor/register", json=doctor_data)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == 1
        assert data["data"]["email"] == doctor_data["email"]

    @pytest.mark.asyncio
    async def test_register_duplicate_license_fails(self, client: AsyncClient, doctor_data):
        await client.post("/api/v1/doctor/register", json=doctor_data)
        response = await client.post("/api/v1/doctor/register", json=doctor_data)
        assert response.status_code == 409


class TestDoctorLogin:
    @pytest.mark.asyncio
    async def test_login_unverified_doctor_fails(self, client: AsyncClient, doctor_data):
        await client.post("/api/v1/doctor/register", json=doctor_data)
        response = await client.post(
            "/api/v1/doctor/login",
            data={"username": doctor_data["email"], "password": doctor_data["password"]},
        )
        assert response.status_code == 401
        assert "not verified" in response.json()["message"].lower()
