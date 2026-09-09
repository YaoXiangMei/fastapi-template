# 多角色认证架构设计

**日期**: 2026-09-09  
**状态**: 已批准  
**作者**: 架构设计讨论

---

## 1. 概述

将现有的单一 `users` 表认证系统重构为多角色独立认证架构，支持三种用户类型：

- **Patient（患者）** — 用户端 App
- **Doctor（医生）** — 医生工作台
- **Admin（管理员）** — 管理后台

每个角色拥有独立的数据库表、独立的登录端点、独立的 API 路径前缀，但共享统一的 JWT 认证基础设施。

---

## 2. 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 用户表结构 | 独立表（每角色一张） | 不同角色的字段差异大，业务隔离清晰 |
| Token 角色标识 | 不携带，靠 API 路径区分 | 简化 token 结构，安全性更好 |
| 登录入口 | 各端口独立 | 三个不同应用端点，各自认证 |
| 跨角色存在 | 不允许 | 一个人只有一个身份 |
| 认证依赖 | 工厂模式生成 | 减少重复代码，保持一致性 |

---

## 3. 数据模型

### 3.1 表结构

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│      patients       │     │       doctors       │     │       admins        │
├─────────────────────┤     ├─────────────────────┤     ├─────────────────────┤
│ id (UUID, PK)       │     │ id (UUID, PK)       │     │ id (UUID, PK)       │
│ email (unique)      │     │ email (unique)      │     │ username (unique)   │
│ hashed_password     │     │ hashed_password     │     │ hashed_password     │
│ full_name           │     │ full_name           │     │ full_name           │
│ phone               │     │ phone               │     │ email               │
│ gender              │     │ license_no (unique) │     │ phone               │
│ birth_date          │     │ specialty           │     │ last_login          │
│ is_active           │     │ department          │     │ is_active           │
│ created_at          │     │ title               │     │ created_at          │
│ updated_at          │     │ is_active           │     │ updated_at          │
│                     │     │ is_verified         │     │                     │
│                     │     │ created_at          │     │                     │
│                     │     │ updated_at          │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### 3.2 共享 Mixin

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class AuthUserMixin:
    """认证用户共享字段 mixin"""
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

### 3.3 字段说明

**Patient（患者）**:
- `gender`: 性别（male/female/other）
- `birth_date`: 出生日期，用于年龄计算

**Doctor（医生）**:
- `license_no`: 执业证号，唯一约束
- `specialty`: 专科（如 cardiology, neurology）
- `department`: 科室
- `title`: 职称（如 attending, associate_chief, chief）
- `is_verified`: 执业审核状态，注册时默认 False

**Admin（管理员）**:
- `username`: 登录用户名（管理后台习惯用用户名而非邮箱）
- `last_login`: 最后登录时间，用于安全审计

---

## 4. 核心认证工厂

### 4.1 文件位置

`app/core/auth_factory.py`

### 4.2 实现

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
    
    Example:
        oauth2_scheme, get_current_doctor = create_auth_dependency(
            Doctor, "/api/v1/doctor/login"
        )
    """
    scheme = OAuth2PasswordBearer(tokenUrl=token_url, auto_error=True)
    
    async def dependency(
        token: str = Depends(scheme),
        db: AsyncSession = Depends(get_db),
    ):
        # 解码并验证 JWT
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            raise UnauthorizedException("Invalid or expired token")
        
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token")
        
        # 查询对应角色的用户表
        result = await db.execute(
            select(model).where(model.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UnauthorizedException("User not found")
        
        if not getattr(user, "is_active", True):
            raise UnauthorizedException("Account is disabled")
        
        # 特殊检查：医生需要验证执业状态
        if hasattr(user, "is_verified") and not user.is_verified:
            raise UnauthorizedException(
                "Account not verified, please wait for admin approval"
            )
        
        return user
    
    return scheme, dependency
```

---

## 5. 模块结构

### 5.1 目录布局

```
app/modules/
├── patient/
│   ├── __init__.py
│   ├── models.py        # Patient 表定义
│   ├── schemas.py       # PatientCreate, PatientRead, PatientUpdate
│   ├── service.py       # register(), login(), refresh(), logout()
│   ├── router.py        # /login, /register, /refresh, /logout, /me
│   └── deps.py          # get_current_patient 认证依赖
├── doctor/
│   ├── __init__.py
│   ├── models.py
│   ├── schemas.py
│   ├── service.py
│   ├── router.py
│   └── deps.py          # get_current_doctor 认证依赖
├── admin/
│   ├── __init__.py
│   ├── models.py
│   ├── schemas.py
│   ├── service.py       # login(), refresh(), logout()（无 register）
│   ├── router.py
│   └── deps.py          # get_current_admin 认证依赖
└── user/                # 保留旧模块，后续可迁移或删除
    └── ...
```

### 5.2 各模块 `deps.py` 示例

```python
# app/modules/doctor/deps.py
"""医生端认证依赖。"""

from app.core.auth_factory import create_auth_dependency
from app.modules.doctor.models import Doctor

oauth2_scheme, get_current_doctor = create_auth_dependency(
    Doctor,
    token_url="/api/v1/doctor/login",
)

__all__ = ["oauth2_scheme", "get_current_doctor"]
```

---

## 6. API 路由设计

### 6.1 路由总览

```
/api/v1/patient/
  ├── POST /register       # 患者注册
  ├── POST /login          # 患者登录 → 返回 token
  ├── POST /refresh        # 刷新 token
  ├── POST /logout         # 登出（吊销 token）
  └── GET  /me             # 获取当前患者信息（需认证）

/api/v1/doctor/
  ├── POST /register       # 医生注册（is_verified=False，需审核）
  ├── POST /login          # 医生登录 → 返回 token
  ├── POST /refresh        # 刷新 token
  ├── POST /logout         # 登出
  └── GET  /me             # 获取当前医生信息（需认证）

/api/v1/admin/
  ├── POST /login          # 管理员登录（无注册入口）
  ├── POST /refresh        # 刷新 token
  ├── POST /logout         # 登出
  └── GET  /me             # 获取当前管理员信息（需认证）
```

### 6.2 路由注册

```python
# app/api/router.py
from fastapi import APIRouter
from app.modules.patient.router import router as patient_router
from app.modules.doctor.router import router as doctor_router
from app.modules.admin.router import router as admin_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(patient_router, prefix="/patient", tags=["patient"])
api_router.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
```

### 6.3 Router 示例（Doctor）

```python
# app/modules/doctor/router.py
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.doctor import service
from app.modules.doctor.schemas import DoctorCreate, DoctorRead, TokenResponse
from app.modules.doctor.deps import get_current_doctor
from app.modules.doctor.models import Doctor

router = APIRouter()


@router.post("/register", response_model=ApiResponse[DoctorRead], status_code=201)
async def register(data: DoctorCreate, db: AsyncSession = Depends(get_db)):
    """医生注册（需管理员审核后激活）"""
    doctor = await service.register(db, data)
    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(doctor)}


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """医生登录，返回 JWT token"""
    return await service.login(db, form.username, form.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新 token"""
    return await service.refresh(db, data.refresh_token)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """登出，吊销 refresh token"""
    await service.logout(db, data.refresh_token)
    return {"status": 1, "message": "success", "data": None}


@router.get("/me", response_model=ApiResponse[DoctorRead])
async def get_me(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取当前登录医生的信息"""
    return {"status": 1, "message": "success", "data": DoctorRead.model_validate(current_doctor)}
```

---

## 7. Service 层设计

### 7.1 登录逻辑（以 Doctor 为例）

```python
# app/modules/doctor/service.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
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


async def register(db: AsyncSession, data: DoctorCreate) -> Doctor:
    """医生注册，默认 is_verified=False"""
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
    await db.commit()
    await db.refresh(doctor)
    return doctor


async def login(db: AsyncSession, email: str, password: str) -> dict:
    """医生登录，验证执业状态"""
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
    
    # Redis 存储 refresh token，key 包含角色前缀
    redis = get_redis()
    await redis.setex(
        f"refresh:doctor:{doctor_id}:{jti}",
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
    """刷新 token"""
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")
    
    doctor_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    
    key = f"refresh:doctor:{doctor_id}:{jti}"
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
        f"refresh:doctor:{doctor_id}:{new_jti}",
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
    """登出，吊销 refresh token"""
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")
    
    doctor_id = payload["sub"]
    jti = payload["jti"]
    redis = get_redis()
    await redis.delete(f"refresh:doctor:{doctor_id}:{jti}")
```

### 7.2 Patient 和 Admin 的 Service

逻辑与 Doctor 相同，差异点：

| 角色 | 差异 |
|------|------|
| Patient | 无 `is_verified` 检查；Redis key 前缀 `refresh:patient:` |
| Doctor | 有 `is_verified` 检查；Redis key 前缀 `refresh:doctor:` |
| Admin | 无 `register()`；Redis key 前缀 `refresh:admin:` |

---

## 8. Token 处理

### 8.1 JWT Payload 结构

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "type": "access",
  "iat": 1725868800,
  "exp": 1725870600
}
```

- **不含角色信息** — 角色由 API 路径决定
- `sub` 是用户的 UUID（字符串格式）

### 8.2 Redis Key 格式

```
refresh:{role}:{user_id}:{jti}

示例：
refresh:patient:550e8400-e29b-41d4-a716-446655440000:abc123...
refresh:doctor:660e8400-e29b-41d4-a716-446655440001:def456...
refresh:admin:770e8400-e29b-41d4-a716-446655440002:ghi789...
```

角色前缀防止跨角色的 refresh token 冲突。

### 8.3 Token 跨端口使用

- 技术上：patient token 访问 doctor 接口会查 `doctors` 表找不到用户，返回 401
- 设计上：不鼓励也不支持跨端口使用
- 如需跨端口，应通过后端服务间调用，而非前端直接传递 token

---

## 9. Swagger UI 集成

### 9.1 多认证方案

每个角色独立的 OAuth2 认证方案：

```python
# app/modules/patient/deps.py
patient_oauth, get_current_patient = create_auth_dependency(Patient, "/api/v1/patient/login")

# app/modules/doctor/deps.py
doctor_oauth, get_current_doctor = create_auth_dependency(Doctor, "/api/v1/doctor/login")

# app/modules/admin/deps.py
admin_oauth, get_current_admin = create_auth_dependency(Admin, "/api/v1/admin/login")
```

Swagger UI 会显示三个独立的 Authorize 入口，分别对应三个登录端点。

### 9.2 Login 接口响应格式

为兼容 Swagger UI 的 OAuth2 流程，login 接口直接返回 `TokenResponse`（不包裹在 `ApiResponse` 中）：

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 10. 错误处理

### 10.1 统一错误格式

```json
{
  "status": 0,
  "message": "错误描述",
  "data": null
}
```

### 10.2 角色特定的错误信息

| 场景 | 错误信息 |
|------|---------|
| 医生未验证 | "Account not verified, please wait for admin approval" |
| Token 无效 | "Invalid or expired token" |
| 用户不存在 | "User not found"（查对应角色的表找不到） |
| 账号禁用 | "Account is disabled" |

### 10.3 跨角色访问

用 patient token 访问 `/api/v1/doctor/me` 时：
- Token 解码成功（JWT 有效）
- 查询 `doctors` 表找不到对应 ID
- 返回 401 "User not found"

---

## 11. 迁移策略

### 阶段 1：创建新模块（不破坏现有代码）

1. 新增 `app/core/auth_factory.py`
2. 新增 `app/modules/patient/` 整个模块
3. 新增 `app/modules/doctor/` 整个模块
4. 新增 `app/modules/admin/` 整个模块
5. 在 `app/api/router.py` 中注册新路由

### 阶段 2：数据库迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "add patient, doctor, admin tables"
alembic upgrade head
```

新增表：
- `patients`
- `doctors`
- `admins`

可选：迁移现有 `users` 表数据到新表（根据业务需求）

### 阶段 3：路由切换

1. 保留旧 `/api/v1/auth/*` 路由，标记为 `deprecated`
2. 新前端应用使用 `/api/v1/patient/*`、`/api/v1/doctor/*`、`/api/v1/admin/*`
3. 逐步迁移旧前端到新路由

### 阶段 4：清理（可选）

1. 确认所有客户端已迁移到新路由
2. 删除旧 `/api/v1/auth/*` 路由
3. 删除旧 `app/modules/user/` 模块
4. 删除旧 `users`、`roles`、`permissions` 表

---

## 12. 新增文件清单

| 文件路径 | 说明 |
|---------|------|
| `app/core/auth_factory.py` | 认证依赖工厂函数 |
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

---

## 13. 测试策略

### 13.1 单元测试

- 每个角色的 `service.py` 独立测试
- `auth_factory.py` 工厂函数测试
- 各角色的 `deps.py` 认证依赖测试

### 13.2 集成测试

- 各角色的完整登录流程（register → login → refresh → logout）
- 跨角色访问测试（用 patient token 访问 doctor 接口应返回 401）
- 医生审核流程测试（注册后 is_verified=False，登录被拒）

### 13.3 API 测试

- 使用 pytest + httpx 测试各端点
- 验证 Swagger UI 的多认证方案是否正确显示

---

## 14. 后续扩展

### 14.1 角色内部 RBAC

医生端可能需要更细粒度的权限控制（如主任医师可以审批新医生）：

```python
# 可在 doctors 表添加 role 字段，或创建 doctor_roles 表
# 复用现有的 RBAC 思路，但只在医生端内部使用
```

### 14.2 跨角色服务调用

如果医生需要查看患者信息：

```python
# 在 doctor 模块的 service 中导入 patient 模块
from app.modules.patient.service import get_patient_by_id

async def get_patient_record(db, patient_id, current_doctor):
    # 验证医生权限后，查询患者信息
    patient = await get_patient_by_id(db, patient_id)
    return patient
```

### 14.3 审计日志

Admin 操作应记录审计日志：

```python
# 可创建 audit_logs 表
# 记录 admin_id, action, target_type, target_id, timestamp
```

---

## 15. 总结

本设计实现了：

✅ **独立用户表** — 每个角色有自己的表，字段独立  
✅ **统一认证** — 共享 JWT 基础设施和认证工厂  
✅ **路径隔离** — API 路径决定认证逻辑，token 不含角色信息  
✅ **模块化** — 各角色模块独立，易维护和扩展  
✅ **向后兼容** — 迁移期间保留旧路由  

设计遵循了 YAGNI 原则，不过度设计，同时为未来扩展留有余地。
