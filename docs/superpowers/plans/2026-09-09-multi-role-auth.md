# 多角色认证架构实施计划

> **对于代理工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实施此计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 将单一 users 表认证系统重构为 Patient/Doctor/Admin 三角色独立认证架构。

**架构：** 每个角色拥有独立的数据库表、API 路径前缀和登录端点。共享 JWT 认证基础设施通过工厂函数生成各角色的认证依赖。API 路径决定认证逻辑，token 不携带角色信息。

**技术栈：** FastAPI, SQLAlchemy (async), Pydantic, PyJWT, Redis, Alembic, pytest

---

## 文件结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `app/core/auth_factory.py` | 通用认证依赖工厂函数 |
| `app/modules/patient/__init__.py` | 患者模块初始化 |
| `app/modules/patient/models.py` | Patient 表定义 |
| `app/modules/patient/schemas.py` | Patient Pydantic 模型 |
| `app/modules/patient/service.py` | 患者业务逻辑 |
| `app/modules/patient/router.py` | 患者 API 路由 |
| `app/modules/patient/deps.py` | 患者认证依赖 |
| `app/modules/doctor/__init__.py` | 医生模块初始化 |
| `app/modules/doctor/models.py` | Doctor 表定义 |
| `app/modules/doctor/schemas.py` | Doctor Pydantic 模型 |
| `app/modules/doctor/service.py` | 医生业务逻辑 |
| `app/modules/doctor/router.py` | 医生 API 路由 |
| `app/modules/doctor/deps.py` | 医生认证依赖 |
| `app/modules/admin/__init__.py` | 管理员模块初始化 |
| `app/modules/admin/models.py` | Admin 表定义 |
| `app/modules/admin/schemas.py` | Admin Pydantic 模型 |
| `app/modules/admin/service.py` | 管理员业务逻辑（无 register） |
| `app/modules/admin/router.py` | 管理员 API 路由 |
| `app/modules/admin/deps.py` | 管理员认证依赖 |
| `app/scripts/seed_admin.py` | 初始管理员种子脚本 |
| `tests/modules/test_patient.py` | 患者模块测试 |
| `tests/modules/test_doctor.py` | 医生模块测试 |
| `tests/modules/test_admin.py` | 管理员模块测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/api/router.py` | 注册新路由 |

---

## 任务 1：创建核心认证工厂

**文件：**
- 创建：`app/core/auth_factory.py`
- 测试：`tests/test_auth_factory.py`

- [ ] **步骤 1：编写认证工厂测试**

创建 `tests/test_auth_factory.py`：

```python
"""认证依赖工厂测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.auth_factory import create_auth_dependency
from app.core.exceptions import UnauthorizedException


class TestCreateAuthDependency:
    """测试 create_auth_dependency 工厂函数。"""

    def test_returns_tuple_of_scheme_and_dependency(self):
        """工厂应返回 (scheme, dependency) 元组。"""
        mock_model = MagicMock()
        scheme, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")
        
        assert scheme is not None
        assert callable(dependency)

    @pytest.mark.anyio
    async def test_dependency_raises_on_invalid_token(self):
        """无效 token 应抛出 UnauthorizedException。"""
        mock_model = MagicMock()
        _, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")
        
        mock_db = AsyncMock()
        
        with patch("app.core.auth_factory.decode_token", side_effect=Exception("Invalid")):
            with pytest.raises(UnauthorizedException, match="Invalid or expired token"):
                await dependency(token="invalid_token", db=mock_db)

    @pytest.mark.anyio
    async def test_dependency_raises_on_wrong_token_type(self):
        """非 access 类型 token 应抛出 UnauthorizedException。"""
        mock_model = MagicMock()
        _, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")
        
        mock_db = AsyncMock()
        
        with patch("app.core.auth_factory.decode_token", return_value={"type": "refresh", "sub": str(uuid4())}):
            with pytest.raises(UnauthorizedException, match="Invalid token type"):
                await dependency(token="refresh_token", db=mock_db)

    @pytest.mark.anyio
    async def test_dependency_raises_on_user_not_found(self):
        """用户不存在应抛出 UnauthorizedException。"""
        mock_model = MagicMock()
        mock_model.id = MagicMock()
        _, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch("app.core.auth_factory.decode_token", return_value={"type": "access", "sub": str(uuid4())}):
            with pytest.raises(UnauthorizedException, match="User not found"):
                await dependency(token="valid_token", db=mock_db)

    @pytest.mark.anyio
    async def test_dependency_raises_on_disabled_account(self):
        """禁用账号应抛出 UnauthorizedException。"""
        mock_model = MagicMock()
        _, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")
        
        mock_user = MagicMock()
        mock_user.is_active = False
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch("app.core.auth_factory.decode_token", return_value={"type": "access", "sub": str(uuid4())}):
            with pytest.raises(UnauthorizedException, match="Account is disabled"):
                await dependency(token="valid_token", db=mock_db)

    @pytest.mark.anyio
    async def test_dependency_raises_on_unverified_account(self):
        """有 is_verified 属性且为 False 的用户应抛出 UnauthorizedException。"""
        mock_model = MagicMock()
        _, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")
        
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.is_verified = False
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch("app.core.auth_factory.decode_token", return_value={"type": "access", "sub": str(uuid4())}):
            with pytest.raises(UnauthorizedException, match="Account not verified"):
                await dependency(token="valid_token", db=mock_db)

    @pytest.mark.anyio
    async def test_dependency_returns_user_on_success(self):
        """有效 token 和用户应返回用户对象。"""
        mock_model = MagicMock()
        _, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")
        
        mock_user = MagicMock()
        mock_user.is_active = True
        # 模拟无 is_verified 属性的模型
        del mock_user.is_verified
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch("app.core.auth_factory.decode_token", return_value={"type": "access", "sub": str(uuid4())}):
            result = await dependency(token="valid_token", db=mock_db)
            assert result == mock_user
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_auth_factory.py -v`
预期：失败，因为 `app.core.auth_factory` 模块不存在

- [ ] **步骤 3：实现认证工厂**

创建 `app/core/auth_factory.py`：

```python
"""通用认证依赖工厂。"""

from typing import Type
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token


def create_auth_dependency(model: Type, token_url: str):
    """为特定角色创建 OAuth2 认证依赖。
    
    Args:
        model: SQLAlchemy 用户模型类（Patient/Doctor/Admin）
        token_url: Swagger UI 的登录端点路径
    
    Returns:
        tuple: (oauth2_scheme, get_current_user_dependency)
    """
    scheme = OAuth2PasswordBearer(tokenUrl=token_url, auto_error=True)
    
    async def dependency(
        token: str = Depends(scheme),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            raise UnauthorizedException("Invalid or expired token")
        
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token")
        
        result = await db.execute(
            select(model).where(model.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UnauthorizedException("User not found")
        
        if not getattr(user, "is_active", True):
            raise UnauthorizedException("Account is disabled")
        
        if hasattr(user, "is_verified") and not user.is_verified:
            raise UnauthorizedException(
                "Account not verified, please wait for admin approval"
            )
        
        return user
    
    return scheme, dependency
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_auth_factory.py -v`
预期：全部通过

- [ ] **步骤 5：提交**

```bash
git add app/core/auth_factory.py tests/test_auth_factory.py
git commit -m "feat: add auth dependency factory for multi-role support"
```

---

## 任务 2：创建 Patient 模块

**文件：**
- 创建：`app/modules/patient/__init__.py`
- 创建：`app/modules/patient/models.py`
- 创建：`app/modules/patient/schemas.py`
- 创建：`app/modules/patient/service.py`
- 创建：`app/modules/patient/router.py`
- 创建：`app/modules/patient/deps.py`
- 测试：`tests/modules/test_patient.py`

- [ ] **步骤 1：编写 Patient 模块测试**

创建 `tests/modules/test_patient.py`：

```python
"""患者模块测试。"""

import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from app.main import app


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
    """患者注册测试。"""

    @pytest.mark.anyio
    async def test_register_patient_success(self, client: AsyncClient, patient_data):
        """成功注册患者。"""
        response = await client.post("/api/v1/patient/register", json=patient_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == 1
        assert data["data"]["email"] == patient_data["email"]
        assert "id" in data["data"]

    @pytest.mark.anyio
    async def test_register_duplicate_email_fails(self, client: AsyncClient, patient_data):
        """重复邮箱注册应失败。"""
        await client.post("/api/v1/patient/register", json=patient_data)
        response = await client.post("/api/v1/patient/register", json=patient_data)
        
        assert response.status_code == 409


class TestPatientLogin:
    """患者登录测试。"""

    @pytest.mark.anyio
    async def test_login_success(self, client: AsyncClient, patient_data):
        """成功登录返回 token。"""
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

    @pytest.mark.anyio
    async def test_login_wrong_password_fails(self, client: AsyncClient, patient_data):
        """密码错误应返回 401。"""
        await client.post("/api/v1/patient/register", json=patient_data)
        
        response = await client.post(
            "/api/v1/patient/login",
            data={"username": patient_data["email"], "password": "wrongpassword"},
        )
        
        assert response.status_code == 401


class TestPatientMe:
    """患者获取个人信息测试。"""

    @pytest.mark.anyio
    async def test_get_me_success(self, client: AsyncClient, patient_data):
        """认证后可以获取个人信息。"""
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

    @pytest.mark.anyio
    async def test_get_me_without_token_fails(self, client: AsyncClient):
        """未认证访问 /me 应返回 401。"""
        response = await client.get("/api/v1/patient/me")
        assert response.status_code == 401


class TestCrossRoleAccess:
    """跨角色访问测试。"""

    @pytest.mark.anyio
    async def test_patient_token_cannot_access_doctor_api(self, client: AsyncClient, patient_data):
        """患者 token 访问医生 API 应返回 401。"""
        await client.post("/api/v1/patient/register", json=patient_data)
        login_response = await client.post(
            "/api/v1/patient/login",
            data={"username": patient_data["email"], "password": patient_data["password"]},
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/doctor/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 401
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/modules/test_patient.py -v`
预期：失败，因为 Patient 模块不存在

- [ ] **步骤 3：创建 Patient 模型**

创建 `app/modules/patient/__init__.py`（空文件）

创建 `app/modules/patient/models.py`：

```python
"""患者模型。"""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class Patient(UUIDMixin, TimestampMixin, Base):
    """患者表。"""

    __tablename__ = "patients"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

- [ ] **步骤 4：创建 Patient Schemas**

创建 `app/modules/patient/schemas.py`：

```python
"""患者 Pydantic 模型。"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class PatientCreate(BaseModel):
    """患者注册请求。"""
    email: EmailStr
    password: str
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    birth_date: date | None = None


class PatientRead(BaseModel):
    """患者信息响应。"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PatientUpdate(BaseModel):
    """患者信息更新。"""
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    birth_date: date | None = None
```

- [ ] **步骤 5：创建 Patient Service**

创建 `app/modules/patient/service.py`：

```python
"""患者业务逻辑。"""

from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.schemas import RefreshRequest, TokenResponse
from app.modules.patient.models import Patient
from app.modules.patient.schemas import PatientCreate


def _refresh_key(user_id: str, jti: str) -> str:
    """患者 refresh token 的 Redis 键。"""
    return f"refresh:patient:{user_id}:{jti}"


async def register(db: AsyncSession, data: PatientCreate) -> Patient:
    """注册新患者。"""
    existing = await db.execute(select(Patient).where(Patient.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictException("Email already registered")

    patient = Patient(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        gender=data.gender,
        birth_date=data.birth_date,
    )
    db.add(patient)
    await db.flush()
    await db.refresh(patient)
    return patient


async def login(db: AsyncSession, email: str, password: str) -> dict:
    """患者登录，返回 token 对。"""
    result = await db.execute(select(Patient).where(Patient.email == email))
    patient = result.scalar_one_or_none()

    if not patient or not verify_password(password, patient.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not patient.is_active:
        raise UnauthorizedException("Account is disabled")

    patient_id = str(patient.id)
    access_token = create_access_token(subject=patient_id)
    refresh_token, jti = create_refresh_token(patient_id)

    redis = get_redis()
    await redis.setex(
        _refresh_key(patient_id, jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    """刷新 token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    patient_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()

    key = _refresh_key(patient_id, jti)
    exists = await redis.get(key)
    if not exists:
        raise UnauthorizedException("Refresh token revoked or expired")

    await redis.delete(key)

    result = await db.execute(select(Patient).where(Patient.id == UUID(patient_id)))
    patient = result.scalar_one_or_none()
    if not patient or not patient.is_active:
        raise UnauthorizedException("User not found or disabled")

    new_access = create_access_token(subject=patient_id)
    new_refresh, new_jti = create_refresh_token(patient_id)

    await redis.setex(
        _refresh_key(patient_id, new_jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(db: AsyncSession, refresh_token: str) -> None:
    """登出，吊销 refresh token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    patient_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(_refresh_key(patient_id, jti))
```

- [ ] **步骤 6：创建 Patient 认证依赖**

创建 `app/modules/patient/deps.py`：

```python
"""患者端认证依赖。"""

from app.core.auth_factory import create_auth_dependency
from app.modules.patient.models import Patient

oauth2_scheme, get_current_patient = create_auth_dependency(
    Patient,
    token_url="/api/v1/patient/login",
)

__all__ = ["oauth2_scheme", "get_current_patient"]
```

- [ ] **步骤 7：创建 Patient 路由**

创建 `app/modules/patient/router.py`：

```python
"""患者 API 路由。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.schemas import RefreshRequest, TokenResponse
from app.modules.patient import service
from app.modules.patient.deps import get_current_patient
from app.modules.patient.models import Patient
from app.modules.patient.schemas import PatientCreate, PatientRead

router = APIRouter()


@router.post("/register", response_model=ApiResponse[PatientRead], status_code=201)
async def register(data: PatientCreate, db: AsyncSession = Depends(get_db)):
    """患者注册。"""
    patient = await service.register(db, data)
    return {"status": 1, "message": "success", "data": PatientRead.model_validate(patient)}


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """患者登录，返回 JWT token。"""
    return await service.login(db, form.username, form.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新 token。"""
    return await service.refresh(db, data.refresh_token)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """登出，吊销 refresh token。"""
    await service.logout(db, data.refresh_token)
    return {"status": 1, "message": "success", "data": None}


@router.get("/me", response_model=ApiResponse[PatientRead])
async def get_me(current_patient: Patient = Depends(get_current_patient)):
    """获取当前登录患者的信息。"""
    return {"status": 1, "message": "success", "data": PatientRead.model_validate(current_patient)}
```

- [ ] **步骤 8：运行测试验证通过**

运行：`pytest tests/modules/test_patient.py -v`
预期：全部通过（如果数据库已迁移）

- [ ] **步骤 9：提交**

```bash
git add app/modules/patient/ tests/modules/test_patient.py
git commit -m "feat: add patient module with registration, login, and auth"
```

---

## 任务 3：创建 Doctor 模块

**文件：**
- 创建：`app/modules/doctor/__init__.py`
- 创建：`app/modules/doctor/models.py`
- 创建：`app/modules/doctor/schemas.py`
- 创建：`app/modules/doctor/service.py`
- 创建：`app/modules/doctor/router.py`
- 创建：`app/modules/doctor/deps.py`
- 测试：`tests/modules/test_doctor.py`

- [ ] **步骤 1：编写 Doctor 模块测试**

创建 `tests/modules/test_doctor.py`：

```python
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
    """医生注册测试。"""

    @pytest.mark.anyio
    async def test_register_doctor_success(self, client: AsyncClient, doctor_data):
        """成功注册医生（默认 is_verified=False）。"""
        response = await client.post("/api/v1/doctor/register", json=doctor_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == 1
        assert data["data"]["email"] == doctor_data["email"]

    @pytest.mark.anyio
    async def test_register_duplicate_license_fails(self, client: AsyncClient, doctor_data):
        """重复执业证号注册应失败。"""
        await client.post("/api/v1/doctor/register", json=doctor_data)
        response = await client.post("/api/v1/doctor/register", json=doctor_data)
        
        assert response.status_code == 409


class TestDoctorLogin:
    """医生登录测试。"""

    @pytest.mark.anyio
    async def test_login_unverified_doctor_fails(self, client: AsyncClient, doctor_data):
        """未审核的医生登录应返回 401。"""
        await client.post("/api/v1/doctor/register", json=doctor_data)
        
        response = await client.post(
            "/api/v1/doctor/login",
            data={"username": doctor_data["email"], "password": doctor_data["password"]},
        )
        
        assert response.status_code == 401
        assert "not verified" in response.json()["message"].lower()

    @pytest.mark.anyio
    async def test_login_verified_doctor_success(self, client: AsyncClient, doctor_data, db_session):
        """已审核的医生可以成功登录。"""
        from app.modules.doctor.models import Doctor
        from app.core.security import hash_password
        
        doctor = Doctor(
            email=doctor_data["email"],
            hashed_password=hash_password(doctor_data["password"]),
            full_name=doctor_data["full_name"],
            phone=doctor_data["phone"],
            license_no=doctor_data["license_no"] + "_verified",
            specialty=doctor_data["specialty"],
            department=doctor_data["department"],
            title=doctor_data["title"],
            is_verified=True,
        )
        db_session.add(doctor)
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/doctor/login",
            data={"username": doctor_data["email"], "password": doctor_data["password"]},
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/modules/test_doctor.py -v`
预期：失败

- [ ] **步骤 3：创建 Doctor 模型**

创建 `app/modules/doctor/__init__.py`（空文件）

创建 `app/modules/doctor/models.py`：

```python
"""医生模型。"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class Doctor(UUIDMixin, TimestampMixin, Base):
    """医生表。"""

    __tablename__ = "doctors"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    license_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

- [ ] **步骤 4：创建 Doctor Schemas**

创建 `app/modules/doctor/schemas.py`：

```python
"""医生 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class DoctorCreate(BaseModel):
    """医生注册请求。"""
    email: EmailStr
    password: str
    full_name: str | None = None
    phone: str | None = None
    license_no: str
    specialty: str | None = None
    department: str | None = None
    title: str | None = None


class DoctorRead(BaseModel):
    """医生信息响应。"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    phone: str | None = None
    license_no: str
    specialty: str | None = None
    department: str | None = None
    title: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class DoctorUpdate(BaseModel):
    """医生信息更新。"""
    full_name: str | None = None
    phone: str | None = None
    specialty: str | None = None
    department: str | None = None
    title: str | None = None
```

- [ ] **步骤 5：创建 Doctor Service**

创建 `app/modules/doctor/service.py`：

```python
"""医生业务逻辑。"""

from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.doctor.models import Doctor
from app.modules.doctor.schemas import DoctorCreate


def _refresh_key(user_id: str, jti: str) -> str:
    """医生 refresh token 的 Redis 键。"""
    return f"refresh:doctor:{user_id}:{jti}"


async def register(db: AsyncSession, data: DoctorCreate) -> Doctor:
    """注册新医生（默认 is_verified=False）。"""
    existing_email = await db.execute(select(Doctor).where(Doctor.email == data.email))
    if existing_email.scalar_one_or_none():
        raise ConflictException("Email already registered")

    existing_license = await db.execute(select(Doctor).where(Doctor.license_no == data.license_no))
    if existing_license.scalar_one_or_none():
        raise ConflictException("License number already registered")

    doctor = Doctor(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        license_no=data.license_no,
        specialty=data.specialty,
        department=data.department,
        title=data.title,
        is_verified=False,
    )
    db.add(doctor)
    await db.flush()
    await db.refresh(doctor)
    return doctor


async def login(db: AsyncSession, email: str, password: str) -> dict:
    """医生登录，验证执业状态。"""
    result = await db.execute(select(Doctor).where(Doctor.email == email))
    doctor = result.scalar_one_or_none()

    if not doctor or not verify_password(password, doctor.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not doctor.is_active:
        raise UnauthorizedException("Account is disabled")
    if not doctor.is_verified:
        raise UnauthorizedException("Account not verified, please wait for admin approval")

    doctor_id = str(doctor.id)
    access_token = create_access_token(subject=doctor_id)
    refresh_token, jti = create_refresh_token(doctor_id)

    redis = get_redis()
    await redis.setex(
        _refresh_key(doctor_id, jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    """刷新 token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    doctor_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()

    key = _refresh_key(doctor_id, jti)
    exists = await redis.get(key)
    if not exists:
        raise UnauthorizedException("Refresh token revoked or expired")

    await redis.delete(key)

    result = await db.execute(select(Doctor).where(Doctor.id == UUID(doctor_id)))
    doctor = result.scalar_one_or_none()
    if not doctor or not doctor.is_active:
        raise UnauthorizedException("User not found or disabled")

    new_access = create_access_token(subject=doctor_id)
    new_refresh, new_jti = create_refresh_token(doctor_id)

    await redis.setex(
        _refresh_key(doctor_id, new_jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(db: AsyncSession, refresh_token: str) -> None:
    """登出，吊销 refresh token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    doctor_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(_refresh_key(doctor_id, jti))
```

- [ ] **步骤 6：创建 Doctor 认证依赖**

创建 `app/modules/doctor/deps.py`：

```python
"""医生端认证依赖。"""

from app.core.auth_factory import create_auth_dependency
from app.modules.doctor.models import Doctor

oauth2_scheme, get_current_doctor = create_auth_dependency(
    Doctor,
    token_url="/api/v1/doctor/login",
)

__all__ = ["oauth2_scheme", "get_current_doctor"]
```

- [ ] **步骤 7：创建 Doctor 路由**

创建 `app/modules/doctor/router.py`：

```python
"""医生 API 路由。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.schemas import RefreshRequest, TokenResponse
from app.modules.doctor import service
from app.modules.doctor.deps import get_current_doctor
from app.modules.doctor.models import Doctor
from app.modules.doctor.schemas import DoctorCreate, DoctorRead

router = APIRouter()


@router.post("/register", response_model=ApiResponse[DoctorRead], status_code=201)
async def register(data: DoctorCreate, db: AsyncSession = Depends(get_db)):
    """医生注册（需管理员审核后激活）。"""
    doctor = await service.register(db, data)
    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(doctor)}


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """医生登录，返回 JWT token。"""
    return await service.login(db, form.username, form.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新 token。"""
    return await service.refresh(db, data.refresh_token)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """登出，吊销 refresh token。"""
    await service.logout(db, data.refresh_token)
    return {"status": 1, "message": "success", "data": None}


@router.get("/me", response_model=ApiResponse[DoctorRead])
async def get_me(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取当前登录医生的信息。"""
    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(current_doctor)}
```

- [ ] **步骤 8：运行测试验证通过**

运行：`pytest tests/modules/test_doctor.py -v`
预期：全部通过

- [ ] **步骤 9：提交**

```bash
git add app/modules/doctor/ tests/modules/test_doctor.py
git commit -m "feat: add doctor module with verification workflow"
```

---

## 任务 4：创建 Admin 模块

**文件：**
- 创建：`app/modules/admin/__init__.py`
- 创建：`app/modules/admin/models.py`
- 创建：`app/modules/admin/schemas.py`
- 创建：`app/modules/admin/service.py`
- 创建：`app/modules/admin/router.py`
- 创建：`app/modules/admin/deps.py`
- 测试：`tests/modules/test_admin.py`

- [ ] **步骤 1：编写 Admin 模块测试**

创建 `tests/modules/test_admin.py`：

```python
"""管理员模块测试。"""

import pytest
from httpx import AsyncClient


class TestAdminLogin:
    """管理员登录测试。"""

    @pytest.mark.anyio
    async def test_login_success(self, client: AsyncClient, admin_user):
        """管理员成功登录。"""
        response = await client.post(
            "/api/v1/admin/login",
            data={"username": "admin", "password": "admin123456"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.anyio
    async def test_login_wrong_password_fails(self, client: AsyncClient, admin_user):
        """密码错误应返回 401。"""
        response = await client.post(
            "/api/v1/admin/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        
        assert response.status_code == 401


class TestAdminMe:
    """管理员获取个人信息测试。"""

    @pytest.mark.anyio
    async def test_get_me_success(self, client: AsyncClient, admin_user):
        """认证后可以获取管理员信息。"""
        login_response = await client.post(
            "/api/v1/admin/login",
            data={"username": "admin", "password": "admin123456"},
        )
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/v1/admin/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "admin"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/modules/test_admin.py -v`
预期：失败

- [ ] **步骤 3：创建 Admin 模型**

创建 `app/modules/admin/__init__.py`（空文件）

创建 `app/modules/admin/models.py`：

```python
"""管理员模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class Admin(UUIDMixin, TimestampMixin, Base):
    """管理员表。"""

    __tablename__ = "admins"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

- [ ] **步骤 4：创建 Admin Schemas**

创建 `app/modules/admin/schemas.py`：

```python
"""管理员 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminRead(BaseModel):
    """管理员信息响应。"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    last_login: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **步骤 5：创建 Admin Service**

创建 `app/modules/admin/service.py`：

```python
"""管理员业务逻辑。"""

from datetime import datetime, timezone
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.admin.models import Admin


def _refresh_key(user_id: str, jti: str) -> str:
    """管理员 refresh token 的 Redis 键。"""
    return f"refresh:admin:{user_id}:{jti}"


async def login(db: AsyncSession, username: str, password: str) -> dict:
    """管理员登录，返回 token 对。"""
    result = await db.execute(select(Admin).where(Admin.username == username))
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(password, admin.hashed_password):
        raise UnauthorizedException("Invalid username or password")
    if not admin.is_active:
        raise UnauthorizedException("Account is disabled")

    admin_id = str(admin.id)
    access_token = create_access_token(subject=admin_id)
    refresh_token, jti = create_refresh_token(admin_id)

    redis = get_redis()
    await redis.setex(
        _refresh_key(admin_id, jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    # 更新最后登录时间
    admin.last_login = datetime.now(timezone.utc)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    """刷新 token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    admin_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()

    key = _refresh_key(admin_id, jti)
    exists = await redis.get(key)
    if not exists:
        raise UnauthorizedException("Refresh token revoked or expired")

    await redis.delete(key)

    result = await db.execute(select(Admin).where(Admin.id == UUID(admin_id)))
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        raise UnauthorizedException("User not found or disabled")

    new_access = create_access_token(subject=admin_id)
    new_refresh, new_jti = create_refresh_token(admin_id)

    await redis.setex(
        _refresh_key(admin_id, new_jti),
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(db: AsyncSession, refresh_token: str) -> None:
    """登出，吊销 refresh token。"""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    admin_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(_refresh_key(admin_id, jti))
```

- [ ] **步骤 6：创建 Admin 认证依赖**

创建 `app/modules/admin/deps.py`：

```python
"""管理员端认证依赖。"""

from app.core.auth_factory import create_auth_dependency
from app.modules.admin.models import Admin

oauth2_scheme, get_current_admin = create_auth_dependency(
    Admin,
    token_url="/api/v1/admin/login",
)

__all__ = ["oauth2_scheme", "get_current_admin"]
```

- [ ] **步骤 7：创建 Admin 路由**

创建 `app/modules/admin/router.py`：

```python
"""管理员 API 路由。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.admin import service
from app.modules.admin.deps import get_current_admin
from app.modules.admin.models import Admin
from app.modules.admin.schemas import AdminRead
from app.modules.auth.schemas import RefreshRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """管理员登录，返回 JWT token。"""
    return await service.login(db, form.username, form.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新 token。"""
    return await service.refresh(db, data.refresh_token)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """登出，吊销 refresh token。"""
    await service.logout(db, data.refresh_token)
    return {"status": 1, "message": "success", "data": None}


@router.get("/me", response_model=ApiResponse[AdminRead])
async def get_me(current_admin: Admin = Depends(get_current_admin)):
    """获取当前登录管理员的信息。"""
    return {"status": 1, "message": "success", "data": AdminRead.model_validate(current_admin)}
```

- [ ] **步骤 8：运行测试验证通过**

运行：`pytest tests/modules/test_admin.py -v`
预期：全部通过

- [ ] **步骤 9：提交**

```bash
git add app/modules/admin/ tests/modules/test_admin.py
git commit -m "feat: add admin module with login and audit logging"
```

---

## 任务 5：注册路由并创建数据库迁移

**文件：**
- 修改：`app/api/router.py`

- [ ] **步骤 1：修改 API 路由注册**

编辑 `app/api/router.py`：

```python
"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.doctor.router import router as doctor_router
from app.modules.patient.router import router as patient_router
from app.modules.user.router import (
    permissions_router,
    roles_router,
    router as users_router,
)
from app.modules.vector.router import router as documents_router

api_router = APIRouter(prefix="/api/v1")

# 旧路由（保留向后兼容）
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(documents_router)

# 新多角色路由
api_router.include_router(patient_router, prefix="/patient", tags=["patient"])
api_router.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
```

- [ ] **步骤 2：生成数据库迁移**

运行：`alembic revision --autogenerate -m "add patient, doctor, admin tables"`

- [ ] **步骤 3：检查迁移文件**

打开生成的迁移文件，确认包含：
- 创建 `patients` 表
- 创建 `doctors` 表
- 创建 `admins` 表

- [ ] **步骤 4：执行迁移**

运行：`alembic upgrade head`

- [ ] **步骤 5：运行全部测试**

运行：`pytest tests/ -v`
预期：全部通过

- [ ] **步骤 6：提交**

```bash
git add app/api/router.py alembic/versions/
git commit -m "feat: register multi-role routes and add database migration"
```

---

## 任务 6：创建 Admin 种子脚本

**文件：**
- 创建：`app/scripts/seed_admin.py`

- [ ] **步骤 1：创建种子脚本**

创建 `app/scripts/seed_admin.py`：

```python
"""初始管理员种子脚本。

用法：
    python -m app.scripts.seed_admin
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger
from app.core.security import hash_password
from app.modules.admin.models import Admin


async def seed_admin():
    """创建初始管理员账号。"""
    async with async_session_factory() as db:
        username = settings.SUPERUSER_EMAIL.split("@")[0] if settings.SUPERUSER_EMAIL else "admin"
        password = settings.SUPERUSER_PASSWORD or "admin123456"
        email = settings.SUPERUSER_EMAIL or "admin@example.com"

        # 检查是否已存在
        result = await db.execute(select(Admin).where(Admin.username == username))
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info("Admin account already exists: {}", username)
            return

        admin = Admin(
            username=username,
            hashed_password=hash_password(password),
            full_name="System Admin",
            email=email,
        )
        db.add(admin)
        await db.commit()
        
        logger.info("Created admin account: {} ({})", username, email)


if __name__ == "__main__":
    asyncio.run(seed_admin())
```

- [ ] **步骤 2：运行种子脚本**

运行：`python -m app.scripts.seed_admin`
预期：创建管理员账号

- [ ] **步骤 3：提交**

```bash
git add app/scripts/seed_admin.py
git commit -m "feat: add admin seed script for initial setup"
```

---

## 任务 7：更新测试 conftest

**文件：**
- 修改：`tests/conftest.py`

- [ ] **步骤 1：添加 admin_user fixture**

编辑 `tests/conftest.py`，添加：

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import async_session_factory, get_db
from app.modules.admin.models import Admin
from app.core.security import hash_password


@pytest.fixture
async def db_session():
    """提供数据库会话。"""
    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """提供测试客户端。"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session):
    """创建测试管理员。"""
    admin = Admin(
        username="admin",
        hashed_password=hash_password("admin123456"),
        full_name="Test Admin",
        email="admin@test.com",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin
```

- [ ] **步骤 2：运行全部测试**

运行：`pytest tests/ -v`
预期：全部通过

- [ ] **步骤 3：提交**

```bash
git add tests/conftest.py
git commit -m "test: add fixtures for multi-role auth tests"
```

---

## 任务 8：验证 Swagger UI 集成

- [ ] **步骤 1：启动应用**

运行：`uvicorn app.main:app --reload`

- [ ] **步骤 2：打开 Swagger UI**

打开：http://localhost:8000/docs

- [ ] **步骤 3：验证三个认证方案**

点击 "Authorize" 按钮，确认显示：
- patientAuth（POST /api/v1/patient/login）
- doctorAuth（POST /api/v1/doctor/login）
- adminAuth（POST /api/v1/admin/login）

- [ ] **步骤 4：测试患者登录流程**

1. 使用 /api/v1/patient/register 注册
2. 使用 Authorize 选择 patientAuth 登录
3. 访问 /api/v1/patient/me 确认返回患者信息

- [ ] **步骤 5：测试跨角色访问**

使用 patient token 访问 /api/v1/doctor/me，确认返回 401

- [ ] **步骤 6：最终提交**

```bash
git add -A
git commit -m "feat: complete multi-role auth implementation"
```

---

## 完成标准

- [ ] `app/core/auth_factory.py` 测试全部通过
- [ ] Patient 模块测试全部通过
- [ ] Doctor 模块测试全部通过（含 is_verified 检查）
- [ ] Admin 模块测试全部通过
- [ ] 数据库迁移成功创建三张新表
- [ ] Swagger UI 显示三个认证方案
- [ ] 跨角色访问返回 401
- [ ] 所有现有测试仍然通过
