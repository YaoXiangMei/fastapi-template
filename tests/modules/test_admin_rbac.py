"""Admin RBAC 权限系统测试。"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.admin.models import Admin, AdminPermission, AdminRole


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

    # 刷新 admin 以加载 roles 关系
    await db_session.refresh(admin, ["roles"])

    admin.roles.append(role)
    await db_session.flush()

    # 重新加载，使用 selectinload 避免懒加载
    from sqlalchemy.orm import selectinload
    result = await db_session.execute(
        select(Admin).options(selectinload(Admin.roles)).where(Admin.id == admin.id)
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

    # 刷新 role 以加载 permissions 关系
    await db_session.refresh(role, ["permissions"])

    role.permissions.append(perm)
    await db_session.flush()

    # 重新加载，使用 selectinload 避免懒加载
    from sqlalchemy.orm import selectinload
    result = await db_session.execute(
        select(AdminRole).options(selectinload(AdminRole.permissions)).where(AdminRole.id == role.id)
    )
    loaded_role = result.scalar_one()
    assert len(loaded_role.permissions) == 1
    assert loaded_role.permissions[0].code == "doctor:view"


@pytest.mark.asyncio
async def test_superuser_can_create_permission(
    client: AsyncClient, db_session: AsyncSession, fake_redis
):
    """超级管理员可以创建权限。"""
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

    resp = await client.post(
        "/api/v1/admin/permissions",
        json={
            "code": "test:permission",
            "name": "测试权限",
            "description": "测试用"
        }
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["code"] == "test:permission"


@pytest.mark.asyncio
async def test_non_superuser_cannot_create_permission(
    client: AsyncClient, db_session: AsyncSession, fake_redis
):
    """非超级管理员不能创建权限。"""
    admin = Admin(
        username="normal",
        hashed_password=hash_password("pass"),
        is_superuser=False,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    token = create_access_token(subject=str(admin.id))
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.post(
        "/api/v1/admin/permissions",
        json={
            "code": "test:permission2",
            "name": "测试权限2",
        }
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_with_permission_can_access_endpoint(
    client: AsyncClient, db_session: AsyncSession, fake_redis
):
    """有权限的管理员可以访问受保护端点。"""
    # 创建权限
    perm = AdminPermission(code="doctor:view", name="查看医生")

    # 创建角色并分配权限
    role = AdminRole(name="医生管理员")
    role.permissions.append(perm)

    # 创建管理员并分配角色
    admin = Admin(
        username="admin_perm",
        hashed_password=hash_password("pass"),
        is_superuser=False,
        is_active=True,
    )
    admin.roles.append(role)

    db_session.add_all([admin, role, perm])
    await db_session.flush()

    token = create_access_token(subject=str(admin.id))
    client.headers["Authorization"] = f"Bearer {token}"

    # 访问需要 doctor:view 权限的端点
    resp = await client.get("/api/v1/admin/test-permission")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_without_permission_cannot_access_endpoint(
    client: AsyncClient, db_session: AsyncSession, fake_redis
):
    """无权限的管理员不能访问受保护端点。"""
    # 创建管理员（无角色）
    admin = Admin(
        username="admin_no_perm",
        hashed_password=hash_password("pass"),
        is_superuser=False,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    token = create_access_token(subject=str(admin.id))
    client.headers["Authorization"] = f"Bearer {token}"

    # 访问需要 doctor:view 权限的端点
    resp = await client.get("/api/v1/admin/test-permission")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_superuser_bypasses_permission_check(
    client: AsyncClient, db_session: AsyncSession, fake_redis
):
    """超级管理员跳过权限检查。"""
    super_admin = Admin(
        username="super_bypass",
        hashed_password=hash_password("pass"),
        is_superuser=True,
        is_active=True,
    )
    db_session.add(super_admin)
    await db_session.flush()

    token = create_access_token(subject=str(super_admin.id))
    client.headers["Authorization"] = f"Bearer {token}"

    # 访问需要 doctor:view 权限的端点
    resp = await client.get("/api/v1/admin/test-permission")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_permissions(
    client: AsyncClient, db_session: AsyncSession, fake_redis
):
    """可以列出所有权限。"""
    # 创建一些权限
    perm1 = AdminPermission(code="test:perm1", name="测试权限1")
    perm2 = AdminPermission(code="test:perm2", name="测试权限2")
    db_session.add_all([perm1, perm2])
    await db_session.flush()

    super_admin = Admin(
        username="super_list",
        hashed_password=hash_password("pass"),
        is_superuser=True,
        is_active=True,
    )
    db_session.add(super_admin)
    await db_session.flush()

    token = create_access_token(subject=str(super_admin.id))
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get("/api/v1/admin/permissions")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    # 应该至少有我们创建的权限
    assert len(body["data"]) >= 2


@pytest.mark.asyncio
async def test_create_role(
    client: AsyncClient, db_session: AsyncSession, fake_redis
):
    """超级管理员可以创建角色。"""
    super_admin = Admin(
        username="super_role",
        hashed_password=hash_password("pass"),
        is_superuser=True,
        is_active=True,
    )
    db_session.add(super_admin)
    await db_session.flush()

    token = create_access_token(subject=str(super_admin.id))
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.post(
        "/api/v1/admin/roles",
        json={
            "name": "测试角色",
            "description": "测试用角色"
        }
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["name"] == "测试角色"
