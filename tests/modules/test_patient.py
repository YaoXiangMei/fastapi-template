"""患者模块测试。"""

import pytest
from httpx import AsyncClient


@pytest.fixture
def patient_data():
    return {
        "email": "patient@test.com",
        "password": "testpassword123",
        "full_name": "Test Patient",
        "phone": "13800138000",
        "gender": "male",
        "birth_date": "1990-01-01",
    }


class TestPatientRegistration:
    @pytest.mark.asyncio
    async def test_register_patient_success(self, client: AsyncClient, patient_data):
        response = await client.post("/api/v1/patient/register", json=patient_data)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == 1
        assert data["data"]["email"] == patient_data["email"]
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, client: AsyncClient, patient_data):
        await client.post("/api/v1/patient/register", json=patient_data)
        response = await client.post("/api/v1/patient/register", json=patient_data)
        assert response.status_code == 409


class TestPatientLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, patient_data):
        await client.post("/api/v1/patient/register", json=patient_data)
        response = await client.post(
            "/api/v1/patient/login",
            data={"username": patient_data["email"], "password": patient_data["password"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(self, client: AsyncClient, patient_data):
        await client.post("/api/v1/patient/register", json=patient_data)
        response = await client.post(
            "/api/v1/patient/login",
            data={"username": patient_data["email"], "password": "wrongpassword"},
        )
        assert response.status_code == 401


class TestPatientMe:
    @pytest.mark.asyncio
    async def test_get_me_success(self, client: AsyncClient, patient_data):
        await client.post("/api/v1/patient/register", json=patient_data)
        login_response = await client.post(
            "/api/v1/patient/login",
            data={"username": patient_data["email"], "password": patient_data["password"]},
        )
        token = login_response.json()["access_token"]
        response = await client.get(
            "/api/v1/patient/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["email"] == patient_data["email"]

    @pytest.mark.asyncio
    async def test_get_me_without_token_fails(self, client: AsyncClient):
        response = await client.get("/api/v1/patient/me")
        assert response.status_code == 401
