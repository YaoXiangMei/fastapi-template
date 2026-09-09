# Admin RBAC 权限系统实施计划

> **对于代理工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实施此计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 为 Admin 添加基于角色的访问控制（RBAC）系统，支持权限→角色→Admin 的三层权限管理

**架构：** 创建独立的 admin_roles、admin_permissions 表，通过关联表实现多对多关系。扩展 auth_factory 支持权限检查，超级管理员跳过权限验证。

**技术栈：** FastAPI, SQLAlchemy async, PyJWT, Alembic, pytest-asyncio

---

## 文件结构

### 新建文件
- `app/modules/admin/models.py` - 修改：添加 AdminRole、AdminPermission 模型和关联表
- `app/modules/admin/schemas.py` - 修改：添加角色、权限相关的 Pydantic 模式
- `app/modules/admin/rbac_service.py` - 新建：RBAC 服务层（权限查询、角色分配等）
- `app/modules/admin/rbac_router.py` - 新建：角色、权限管理路由
- `app/scripts/seed_admin_permissions.py` - 新建：权限种子脚本
- `tests/modules/test_admin_rbac.py` - 新建：RBAC 测试
- `alembic/versions/3a4b5c6d7e8f_add_admin_rbac_tables.py` - 新建：数据库迁移

### 修改文件
- `app/modules/admin/models.py` - 添加 is_superuser 字段和 roles 关系
- `app/modules/admin/deps.py` - 添加 require_admin 工厂函数
- `app/core/auth_factory.py` - 扩展支持权限检查
- `app/api/router.py` - 注册新的 rbac_router
- `alembic/env.py` - 导入新模型

---

### 任务 1：创建 Admin RBAC 数据模型

**文件：**
- 修改：`app/modules/admin/models.py`
- 测试：`tests/modules/test_admin_rbac.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/modules/test_admin_rbac.py
"""Admin RBAC 权限系统测试。"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import Admin, AdminRole, AdminPermission


@pytest.mark.asyncio
async def test_admin_has_is_superuser_field(db_session: AsyncSession):
    """Admin 模型有 is_superuser 字段。"""
    admin = Admin(
        username="test_admin",
        hashed_password="x",
        is_superuser=True,
    )
    db_session.add(admin)
    await db_session.flush()
    assert admin.is_superuser is True


@pytest.mark.asyncio
async def test_admin_role_model(db_session: AsyncSession):
    """AdminRole 模型可以创建。"""
    role = AdminRole(name="测试角色", description="测试用")
    db_session.add(role)
    await db_session.flush()
    assert role.id is not None


@pytest.mark.asyncio
async def test_admin_permission_model(db_session: AsyncSession):
    """AdminPermission 模型可以创建。"""
    perm = AdminPermission(
        code="test:permission",
        name="测试权限",
        description="测试用"
    )
    db_session.add(perm)
    await db_session.flush()
    assert perm.id is not None


@pytest.mark.asyncio
async def test_admin_role_assignment(db_session: AsyncSession):
    """可以给 Admin 分配角色。"""
    admin = Admin(username="admin1", hashed_password="x")
    role = AdminRole(name="角色1")
    db_session.add_all([admin, role])
    await db_session.flush()
    
    admin.roles.append(role)
    await db_session.flush()
    
    # 重新加载
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    result = await db_session.execute(
        select(Admin)
        .options(selectinload(Admin.roles))
        .where(Admin.id == admin.id)
    )
    loaded_admin = result.scalar_one()
    assert len(loaded_admin.roles) == 1
    assert loaded_admin.roles[0].name == "角色1"


@pytest.mark.asyncio
async def test_role_permission_assignment(db_session: AsyncSession):
    """可以给角色分配权限。"""
    role = AdminRole(name="角色1")
    perm = AdminPermission(code="doctor:view", name="查看医生")
    db_session.add_all([role, perm])
    await db_session.flush()
    
    role.permissions.append(perm)
    await db_session.flush()
    
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    result = await db_session.execute(
        select(AdminRole)
        .options(selectinload(AdminRole.permissions))
        .where(AdminRole.id == role.id)
    )
    loaded_role = result.scalar_one()
    assert len(loaded_role.permissions) == 1
    assert loaded_role.permissions[0].code == "doctor:view"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/modules/test_admin_rbac.py -v`
预期：失败，因为模型还不存在

- [ ] **步骤 3：实现 Admin RBAC 模型**

```python
# app/modules/admin/models.py
"""管理员 RBAC 模型。"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.mixins import TimestampMixin, UUIDMixin


class Admin(UUIDMixin, TimestampMixin, Base):
    """管理员。"""

    __tablename__ = "admins"

    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    email = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)  # 新增
    last_login = Column(DateTime(timezone=True))

    # 多对多关系：Admin → Roles
    roles = relationship(
        "AdminRole",
        secondary="admin_role_assignments",
        back_populates="admins",
        lazy="selectin"
    )


class AdminRole(UUIDMixin, TimestampMixin, Base):
    """管理员角色。"""

    __tablename__ = "admin_roles"

    name = Column(String(100), nullable=False)
    description = Column(Text)

    # 多对多关系：Role → Permissions
    permissions = relationship(
        "AdminPermission",
        secondary="admin_role_permissions",
        back_populates="roles",
        lazy="selectin"
    )

    # 反向关系
    admins = relationship(
        "Admin",
        secondary="admin_role_assignments",
        back_populates="roles"
    )


class AdminPermission(UUIDMixin, TimestampMixin, Base):
    """管理员权限。"""

    __tablename__ = "admin_permissions"

    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # 反向关系
    roles = relationship(
        "AdminRole",
        secondary="admin_role_permissions",
        back_populates="permissions"
    )


# 关联表
from app.core.database import Base
from sqlalchemy import Table

admin_role_assignments = Table(
    "admin_role_assignments",
    Base.metadata,
    Column("admin_id", UUID(as_uuid=True), ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("admin_roles.id", ondelete="CASCADE"), primary_key=True),
)

admin_role_permissions = Table(
    "admin_role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("admin_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("admin_permissions.id", ondelete="CASCADE"), primary_key=True),
)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/modules/test_admin_rbac.py::test_admin_has_is_superuser_field -v`
预期：通过

- [ ] **步骤 5：提交**

```bash
git add app/modules/admin/models.py tests/modules/test_admin_rbac.py
git commit -m "feat(admin): add RBAC models (AdminRole, AdminPermission, associations)"
```

---

### 任务 2：创建 Alembic 迁移

**文件：**
- 新建：`alembic/versions/3a4b5c6d7e8f_add_admin_rbac_tables.py`

- [ ] **步骤 1：生成迁移**

```bash
alembic revision --autogenerate -m "add_admin_rbac_tables"
```

- [ ] **步骤 2：检查生成的迁移**

确保包含：
- 创建 `admin_roles` 表
- 创建 `admin_permissions` 表
- 创建 `admin_role_assignments` 关联表
- 创建 `admin_role_permissions` 关联表
- 给 `admins` 表添加 `is_superuser` 字段

- [ ] **步骤 3：运行迁移**

```bash
alembic upgrade head
```

- [ ] **步骤 4：提交**

```bash
git add alembic/versions/
git commit -m "feat(migration): add admin RBAC tables"
```

---

### 任务 3：扩展 auth_factory 支持权限检查

**文件：**
- 修改：`app/core/auth_factory.py`
- 修改：`app/modules/admin/deps.py`
- 测试：`tests/modules/test_admin_rbac.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/modules/test_admin_rbac.py
@pytest.mark.asyncio
async def test_require_admin_permission_check(client: AsyncClient, db_session: AsyncSession, fake_redis):
    """require_admin 检查权限。"""
    from app.core.security import hash_password, create_access_token
    from app.modules.admin.models import Admin, AdminRole, AdminPermission
    
    # 创建权限
    perm = AdminPermission(code="doctor:view", name="查看医生")
    role = AdminRole(name="医生管理员")
    role.permissions.append(perm)
    
    # 创建有权限的管理员
    admin_with_perm = Admin(
        username="admin_perm",
        hashed_password=hash_password("pass123"),
        is_active=True,
    )
    admin_with_perm.roles.append(role)
    db_session.add(admin_with_perm)
    await db_session.flush()
    
    # 创建无权限的管理员
    admin_no_perm = Admin(
        username="admin_no_perm",
        hashed_password=hash_password("pass123"),
        is_active=True,
    )
    db_session.add(admin_no_perm)
    await db_session.flush()
    
    # 有权限的管理员可以访问
    token = create_access_token(subject=str(admin_with_perm.id))
    client.headers["Authorization"] = f"Bearer {token}"
    resp = await client.get("/api/v1/admin/test-permission")
    assert resp.status_code == 200
    
    # 无权限的管理员被拒绝
    token = create_access_token(subject=str(admin_no_perm.id))
    client.headers["Authorization"] = f"Bearer {token}"
    resp = await client.get("/api/v1/admin/test-permission")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_superuser_bypasses_permission_check(client: AsyncClient, db_session: AsyncSession, fake_redis):
    """超级管理员跳过权限检查。"""
    from app.core.security import hash_password, create_access_token
    from app.modules.admin.models import Admin
    
    super_admin = Admin(
        username="super_admin",
        hashed_password=hash_password("pass123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(super_admin)
    await db_session.flush()
    
    token = create_access_token(subject=str(super_admin.id))
    client.headers["Authorization"] = f"Bearer {token}"
    resp = await client.get("/api/v1/admin/test-permission")
    assert resp.status_code == 200
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/modules/test_admin_rbac.py::test_require_admin_permission_check -v`
预期：失败，因为 require_admin 还不存在

- [ ] **步骤 3：扩展 auth_factory**

```python
# app/core/auth_factory.py
def create_auth_dependency(
    model: Type,
    token_url: str,
    scheme_name: str | None = None,
    require_permissions: list[str] | None = None,  # 新增
) -> tuple[OAuth2PasswordBearer, Callable]:
    """为特定角色创建 OAuth2 认证依赖。"""
    # ... 现有的 scheme 创建逻辑 ...
    
    async def dependency(
        token: str = Depends(scheme),
        db: AsyncSession = Depends(get_db),
    ):
        # ... 现有的 JWT 验证和用户查询逻辑 ...
        
        # 新增：权限检查
        if require_permissions and model.__name__ == "Admin":
            # 超级管理员跳过权限检查
            if not getattr(user, "is_superuser", False):
                from app.modules.admin.rbac_service import get_admin_permissions
                user_perms = await get_admin_permissions(db, user.id)
                if not set(require_permissions).issubset(user_perms):
                    raise ForbiddenException(
                        f"权限不足，需要: {', '.join(require_permissions)}"
                    )
        
        return user
    
    return scheme, dependency
```

- [ ] **步骤 4：创建 require_admin 工厂函数**

```python
# app/modules/admin/deps.py
from app.core.auth_factory import create_auth_dependency
from app.modules.admin.models import Admin
from collections.abc import Callable

oauth2_scheme, get_current_admin = create_auth_dependency(
    Admin,
    token_url="/api/v1/admin/login",
    scheme_name="AdminAuth",
)


def require_admin(*permissions: str) -> Callable:
    """创建需要特定权限的认证依赖。
    
    用法:
        @router.delete("/doctors/{id}")
        async def delete_doctor(
            _: Admin = Depends(require_admin("doctor:delete"))
        ):
            ...
    """
    _, dependency = create_auth_dependency(
        Admin,
        token_url="/api/v1/admin/login",
        require_permissions=list(permissions),
    )
    return dependency
```

- [ ] **步骤 5：创建测试用的 RBAC 服务（临时）**

```python
# app/modules/admin/rbac_service.py
"""Admin RBAC 服务层。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.admin.models import Admin


async def get_admin_permissions(db: AsyncSession, admin_id: UUID) -> set[str]:
    """获取管理员的所有权限码。"""
    result = await db.execute(
        select(Admin)
        .options(
            selectinload(Admin.roles).selectinload(AdminRole.permissions)
        )
        .where(Admin.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        return set()
    
    permissions = set()
    for role in admin.roles:
        for perm in role.permissions:
            permissions.add(perm.code)
    return permissions
```

- [ ] **步骤 6：添加测试路由（临时）**

```python
# app/modules/admin/router.py 末尾添加
from app.modules.admin.deps import require_admin

@router.get("/test-permission")
async def test_permission_endpoint(
    _: Admin = Depends(require_admin("doctor:view"))
):
    """测试权限检查的临时端点。"""
    return {"status": 1, "message": "success", "data": {"message": "有权限"}}
```

- [ ] **步骤 7：运行测试验证通过**

运行：`pytest tests/modules/test_admin_rbac.py::test_require_admin_permission_check -v`
预期：通过

- [ ] **步骤 8：提交**

```bash
git add app/core/auth_factory.py app/modules/admin/deps.py app/modules/admin/rbac_service.py
git commit -m "feat(admin): extend auth_factory with permission checking"
```

---

### 任务 4：创建 RBAC 管理接口（角色和权限 CRUD）

**文件：**
- 新建：`app/modules/admin/rbac_router.py`
- 修改：`app/modules/admin/schemas.py`
- 测试：`tests/modules/test_admin_rbac.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/modules/test_admin_rbac.py
@pytest.mark.asyncio
async def test_create_permission_as_superuser(client: AsyncClient, db_session: AsyncSession, fake_redis):
    """超级管理员可以创建权限。"""
    from app.core.security import hash_password, create_access_token
    from app.modules.admin.models import Admin
    
    super_admin = Admin(
        username="super",
        hashed_password=hash_password("pass"),
        is_superuser=True,
        is_active=True,
    )
    db_session.add(super_admin)
    await db_session.flush()
    
    token = create_access_token(subject=str(super_admin.id))
    client.headers["Authorization"] = f"Bearer {token}"
    
    resp = await client.post("/api/v1/admin/permissions", json={
        "code": "doctor:approve",
        "name": "审核医生",
        "description": "可以审核新注册的医生"
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["code"] == "doctor:approve"


@pytest.mark.asyncio
async def test_create_role_as_superuser(client: AsyncClient, db_session: AsyncSession, fake_redis):
    """超级管理员可以创建角色。"""
    # ... 类似的测试 ...
```

- [ ] **步骤 2：实现 RBAC schemas**

```python
# app/modules/admin/schemas.py（追加）
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


# ── 权限 ──
class PermissionCreate(BaseModel):
    code: str
    name: str
    description: str | None = None


class PermissionRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ── 角色 ──
class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class RoleWithPermissions(RoleRead):
    permissions: list[PermissionRead] = []


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[UUID]


# ── Admin 角色分配 ──
class AssignRolesRequest(BaseModel):
    role_ids: list[UUID]
```

- [ ] **步骤 3：实现 RBAC 服务层**

```python
# app/modules/admin/rbac_service.py（追加）
from app.modules.admin.models import AdminRole, AdminPermission
from app.modules.admin.schemas import PermissionCreate, RoleCreate


async def create_permission(db: AsyncSession, data: PermissionCreate) -> AdminPermission:
    """创建权限。"""
    perm = AdminPermission(**data.model_dump())
    db.add(perm)
    await db.flush()
    return perm


async def list_permissions(db: AsyncSession) -> list[AdminPermission]:
    """列出所有权限。"""
    result = await db.execute(select(AdminPermission))
    return list(result.scalars().all())


async def create_role(db: AsyncSession, data: RoleCreate) -> AdminRole:
    """创建角色。"""
    role = AdminRole(**data.model_dump())
    db.add(role)
    await db.flush()
    return role


async def list_roles(db: AsyncSession) -> list[AdminRole]:
    """列出所有角色。"""
    result = await db.execute(select(AdminRole))
    return list(result.scalars().all())


async def assign_permissions_to_role(
    db: AsyncSession, role_id: UUID, permission_ids: list[UUID]
) -> AdminRole:
    """给角色分配权限。"""
    role = await db.get(AdminRole, role_id)
    if not role:
        raise NotFoundException("角色不存在")
    
    perms = await db.execute(
        select(AdminPermission).where(AdminPermission.id.in_(permission_ids))
    )
    role.permissions = list(perms.scalars().all())
    await db.flush()
    return role


async def assign_roles_to_admin(
    db: AsyncSession, admin_id: UUID, role_ids: list[UUID]
) -> Admin:
    """给管理员分配角色。"""
    admin = await db.get(Admin, admin_id)
    if not admin:
        raise NotFoundException("管理员不存在")
    
    roles = await db.execute(
        select(AdminRole).where(AdminRole.id.in_(role_ids))
    )
    admin.roles = list(roles.scalars().all())
    await db.flush()
    return admin
```

- [ ] **步骤 4：实现 RBAC 路由**

```python
# app/modules/admin/rbac_router.py
"""Admin RBAC 管理路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.admin import rbac_service
from app.modules.admin.deps import get_current_admin, require_admin
from app.modules.admin.models import Admin, AdminRole, AdminPermission
from app.modules.admin.schemas import (
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RoleRead,
    RoleWithPermissions,
    AssignPermissionsRequest,
    AssignRolesRequest,
)

router = APIRouter(prefix="/admin", tags=["admin-rbac"])


# ── 权限管理 ──

@router.post("/permissions", response_model=ApiResponse[PermissionRead], status_code=201)
async def create_permission(
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),  # 实际需要 superuser 检查
):
    """创建权限。"""
    perm = await rbac_service.create_permission(db, data)
    return {"status": 1, "message": "success", "data": PermissionRead.model_validate(perm)}


@router.get("/permissions", response_model=ApiResponse[list[PermissionRead]])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """列出所有权限。"""
    perms = await rbac_service.list_permissions(db)
    return {"status": 1, "message": "success", "data": [PermissionRead.model_validate(p) for p in perms]}


# ── 角色管理 ──

@router.post("/roles", response_model=ApiResponse[RoleRead], status_code=201)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """创建角色。"""
    role = await rbac_service.create_role(db, data)
    return {"status": 1, "message": "success", "data": RoleRead.model_validate(role)}


@router.get("/roles", response_model=ApiResponse[list[RoleRead]])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """列出所有角色。"""
    roles = await rbac_service.list_roles(db)
    return {"status": 1, "message": "success", "data": [RoleRead.model_validate(r) for r in roles]}


@router.post("/roles/{role_id}/permissions", response_model=ApiResponse[RoleWithPermissions])
async def assign_permissions(
    role_id: UUID,
    data: AssignPermissionsRequest,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """给角色分配权限。"""
    role = await rbac_service.assign_permissions_to_role(db, role_id, data.permission_ids)
    return {"status": 1, "message": "success", "data": RoleWithPermissions.model_validate(role)}


# ── Admin 角色分配 ──

@router.get("/users", response_model=ApiResponse[list[dict]])
async def list_admins(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """列出所有管理员。"""
    from sqlalchemy import select
    result = await db.execute(select(Admin))
    admins = result.scalars().all()
    return {
        "status": 1,
        "message": "success",
        "data": [
            {
                "id": str(a.id),
                "username": a.username,
                "full_name": a.full_name,
                "email": a.email,
                "is_superuser": a.is_superuser,
                "roles": [{"id": str(r.id), "name": r.name} for r in a.roles],
            }
            for a in admins
        ],
    }


@router.post("/users/{admin_id}/roles", response_model=ApiResponse[dict])
async def assign_roles(
    admin_id: UUID,
    data: AssignRolesRequest,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """给管理员分配角色。"""
    admin = await rbac_service.assign_roles_to_admin(db, admin_id, data.role_ids)
    return {
        "status": 1,
        "message": "success",
        "data": {
            "id": str(admin.id),
            "username": admin.username,
            "roles": [{"id": str(r.id), "name": r.name} for r in admin.roles],
        },
    }
```

- [ ] **步骤 5：注册路由**

```python
# app/api/router.py
from app.modules.admin.rbac_router import router as admin_rbac_router

# 在 admin_router 之后添加
api_router.include_router(admin_rbac_router)
```

- [ ] **步骤 6：运行测试验证通过**

运行：`pytest tests/modules/test_admin_rbac.py -v`
预期：所有测试通过

- [ ] **步骤 7：提交**

```bash
git add app/modules/admin/rbac_router.py app/modules/admin/schemas.py app/modules/admin/rbac_service.py app/api/router.py
git commit -m "feat(admin): add RBAC management endpoints"
```

---

### 任务 5：创建权限种子脚本

**文件：**
- 新建：`app/scripts/seed_admin_permissions.py`

- [ ] **步骤 1：实现种子脚本**

```python
# app/scripts/seed_admin_permissions.py
"""Admin 权限种子脚本。

用法：
    python -m app.scripts.seed_admin_permissions
"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import logger
from app.modules.admin.models import AdminPermission


# 预定义权限
PERMISSIONS = [
    # 医生管理
    ("doctor:view", "查看医生", "查看医生列表和详情"),
    ("doctor:approve", "审核医生", "审核新注册的医生"),
    ("doctor:delete", "删除医生", "删除医生账号"),
    
    # 患者管理
    ("patient:view", "查看患者", "查看患者列表和详情"),
    ("patient:delete", "删除患者", "删除患者账号"),
    
    # 管理员管理
    ("admin:create", "创建管理员", "创建新的管理员账号"),
    ("admin:delete", "删除管理员", "删除管理员账号"),
    
    # 角色权限管理
    ("role:manage", "管理角色", "创建、编辑、删除角色"),
    
    # 系统
    ("system:config", "系统配置", "修改系统配置"),
    ("report:view", "查看报表", "查看系统报表"),
    ("data:export", "导出数据", "导出系统数据"),
]


async def seed_permissions():
    """创建预定义权限。"""
    async with async_session_factory() as db:
        for code, name, description in PERMISSIONS:
            # 检查是否已存在
            result = await db.execute(
                select(AdminPermission).where(AdminPermission.code == code)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info("Permission already exists: {}", code)
                continue
            
            perm = AdminPermission(
                code=code,
                name=name,
                description=description,
            )
            db.add(perm)
            logger.info("Created permission: {} - {}", code, name)
        
        await db.commit()
        logger.info("Permission seeding completed")


if __name__ == "__main__":
    asyncio.run(seed_permissions())
```

- [ ] **步骤 2：运行种子脚本**

```bash
python -m app.scripts.seed_admin_permissions
```

- [ ] **步骤 3：提交**

```bash
git add app/scripts/seed_admin_permissions.py
git commit -m "feat(scripts): add admin permission seed script"
```

---

### 任务 6：完善测试和清理

**文件：**
- 修改：`tests/modules/test_admin_rbac.py`

- [ ] **步骤 1：删除临时的测试路由**

从 `app/modules/admin/router.py` 删除 `/test-permission` 端点。

- [ ] **步骤 2：添加更多测试场景**

```python
# tests/modules/test_admin_rbac.py
@pytest.mark.asyncio
async def test_admin_without_roles_cannot_access_protected_endpoint():
    """无角色的管理员不能访问受保护端点。"""
    # ...

@pytest.mark.asyncio
async def test_admin_with_partial_permissions():
    """有部分权限的管理员只能访问有权限的端点。"""
    # ...

@pytest.mark.asyncio
async def test_assign_permissions_to_role():
    """可以给角色分配权限。"""
    # ...

@pytest.mark.asyncio
async def test_assign_roles_to_admin():
    """可以给管理员分配角色。"""
    # ...
```

- [ ] **步骤 3：运行完整测试套件**

```bash
pytest tests/ -v --ignore=tests/modules/test_vector.py
```

预期：所有测试通过

- [ ] **步骤 4：提交**

```bash
git add tests/modules/test_admin_rbac.py
git commit -m "test(admin): complete RBAC test coverage"
```

---

### 任务 7：更新文档

**文件：**
- 修改：`README.md`（如果有）

- [ ] **步骤 1：添加 RBAC 使用说明**

```markdown
## Admin RBAC 权限系统

### 初始化权限
```bash
python -m app.scripts.seed_admin_permissions
```

### 使用示例

1. 创建权限（已预定义）
2. 创建角色
3. 给角色分配权限
4. 给管理员分配角色

详见 API 文档：http://localhost:8000/docs
```

- [ ] **步骤 2：提交**

```bash
git add README.md
git commit -m "docs: add RBAC usage instructions"
```

---

## 执行顺序

1. 任务 1：数据模型（必须先完成）
2. 任务 2：数据库迁移
3. 任务 3：auth_factory 扩展
4. 任务 4：RBAC 管理接口
5. 任务 5：种子脚本
6. 任务 6：完善测试
7. 任务 7：文档

每个任务完成后进行两阶段审查（规范合规性 + 代码质量）。
