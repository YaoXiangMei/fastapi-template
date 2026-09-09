# Admin RBAC 权限系统设计

## 概述

为 Admin（管理员）角色添加基于角色的访问控制（RBAC）系统，支持细粒度的业务功能权限管理。Patient 和 Doctor 保持独立，不添加权限系统。

## 设计决策

### 1. 范围
- **只给 Admin 添加权限系统**
- Patient 和 Doctor 保持现有的独立认证
- 未来可扩展到 Doctor（如果需要）

### 2. 权限粒度
- **业务功能级别**（如 `doctor:approve`、`patient:view`）
- 不是 API 端点级别

### 3. 角色模型
- **混合模式**：权限 → 角色 → Admin
- **多角色**：一个 Admin 可以有多个角色
- 权限是角色的并集

### 4. 超级管理员
- `is_superuser=True` 的 Admin 跳过所有权限检查
- 拥有系统所有权限

## 数据模型

### 表结构

```sql
-- 1. admins 表（已存在，增加 is_superuser 字段）
admins (
  id UUID PK,
  username VARCHAR UNIQUE,
  hashed_password VARCHAR,
  full_name VARCHAR,
  email VARCHAR,
  is_active BOOLEAN DEFAULT true,
  is_superuser BOOLEAN DEFAULT false,  -- 超级管理员标识
  last_login TIMESTAMP,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- 2. admin_roles 表（新增）
admin_roles (
  id UUID PK,
  name VARCHAR(100),              -- 角色名称，无唯一约束
  description TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- 3. admin_permissions 表（新增）
admin_permissions (
  id UUID PK,
  code VARCHAR(100) UNIQUE,       -- 权限码，如 'doctor:approve'
  name VARCHAR(100),
  description TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- 4. admin_role_assignments 关联表（新增）
admin_role_assignments (
  admin_id UUID FK → admins.id ON DELETE CASCADE,
  role_id UUID FK → admin_roles.id ON DELETE CASCADE,
  PRIMARY KEY (admin_id, role_id)
)

-- 5. admin_role_permissions 关联表（新增）
admin_role_permissions (
  role_id UUID FK → admin_roles.id ON DELETE CASCADE,
  permission_id UUID FK → admin_permissions.id ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
)
```

### 模型关系

```python
Admin
  ↓ (多对多，通过 admin_role_assignments)
AdminRole
  ↓ (多对多，通过 admin_role_permissions)
AdminPermission
```

## 权限检查逻辑

### 认证依赖工厂扩展

```python
def create_auth_dependency(
    model: Type, 
    token_url: str, 
    scheme_name: str | None = None,
    require_permissions: list[str] | None = None
) -> tuple[OAuth2PasswordBearer, Callable]:
    """创建认证依赖，可选权限检查。"""
    
    async def dependency(token: str = Depends(scheme), db = Depends(get_db)):
        # 1. 验证 JWT token
        # 2. 查询用户
        # 3. 检查 is_active
        
        # 4. 如果是 Admin 且需要权限检查
        if model == Admin and require_permissions:
            # 超级管理员跳过权限检查
            if not user.is_superuser:
                user_perms = await get_admin_permissions(db, user.id)
                if not set(require_permissions).issubset(user_perms):
                    raise ForbiddenException("权限不足")
        
        return user
```

### 使用方式

```python
# 基础认证（无权限要求）
oauth2_scheme, get_current_admin = create_auth_dependency(
    Admin, token_url="/api/v1/admin/login", scheme_name="AdminAuth"
)

# 需要特定权限的认证
def require_admin(*permissions: str):
    """工厂函数：创建需要特定权限的认证依赖。"""
    _, dependency = create_auth_dependency(
        Admin, 
        token_url="/api/v1/admin/login",
        require_permissions=list(permissions)
    )
    return dependency

# 路由中使用
@router.delete("/doctors/{id}")
async def delete_doctor(
    _: Admin = Depends(require_admin("doctor:delete"))
):
    ...
```

## 管理接口

### 角色管理（需要超级管理员权限）

```
POST   /api/v1/admin/roles              # 创建角色
GET    /api/v1/admin/roles              # 列出所有角色
GET    /api/v1/admin/roles/{id}         # 获取角色详情
PUT    /api/v1/admin/roles/{id}         # 更新角色
DELETE /api/v1/admin/roles/{id}         # 删除角色
POST   /api/v1/admin/roles/{id}/permissions  # 给角色分配权限
```

### 权限管理（需要超级管理员权限）

```
POST   /api/v1/admin/permissions        # 创建权限
GET    /api/v1/admin/permissions        # 列出所有权限
DELETE /api/v1/admin/permissions/{id}   # 删除权限
```

### Admin 角色分配（需要超级管理员权限）

```
GET    /api/v1/admin/users              # 列出所有管理员
POST   /api/v1/admin/users/{id}/roles   # 给管理员分配角色
DELETE /api/v1/admin/users/{id}/roles/{role_id}  # 移除管理员的角色
```

## 预定义权限码

### 医生管理
- `doctor:view` - 查看医生列表和详情
- `doctor:approve` - 审核新注册的医生
- `doctor:delete` - 删除医生账号

### 患者管理
- `patient:view` - 查看患者列表和详情
- `patient:delete` - 删除患者账号

### 管理员管理
- `admin:create` - 创建新的管理员账号
- `admin:delete` - 删除管理员账号

### 角色权限管理
- `role:manage` - 创建、编辑、删除角色

### 系统
- `system:config` - 修改系统配置
- `report:view` - 查看系统报表
- `data:export` - 导出系统数据

## 服务层实现

### 核心函数

```python
async def get_admin_permissions(db: AsyncSession, admin_id: UUID) -> set[str]:
    """获取管理员的所有权限码。"""
    # 查询 Admin，加载 roles 和 permissions
    # 收集所有权限码并返回集合

async def assign_roles_to_admin(
    db: AsyncSession, admin_id: UUID, role_ids: list[UUID]
) -> Admin:
    """给管理员分配角色。"""

async def assign_permissions_to_role(
    db: AsyncSession, role_id: UUID, permission_ids: list[UUID]
) -> AdminRole:
    """给角色分配权限。"""
```

## 错误处理

- **权限不足**：`403 Forbidden` - "权限不足，需要: doctor:approve"
- **角色不存在**：`404 Not Found` - "角色不存在"
- **权限码已存在**：`409 Conflict` - "权限码 'doctor:approve' 已存在"
- **不能删除超级管理员**：`403 Forbidden` - "不能删除超级管理员账号"

## 种子脚本

创建 `app/scripts/seed_admin_permissions.py`：
- 创建所有预定义权限
- 可选：创建默认角色（如"超级管理员"、"医生管理员"等）

## 迁移策略

1. 创建新表：`admin_roles`、`admin_permissions`、`admin_role_assignments`、`admin_role_permissions`
2. 给 `admins` 表添加 `is_superuser` 字段
3. 运行种子脚本创建预定义权限

## 测试策略

1. **单元测试**
   - 权限检查逻辑
   - 角色分配
   - 权限分配

2. **集成测试**
   - 管理员登录后访问受保护接口
   - 超级管理员跳过权限检查
   - 权限不足返回 403

3. **测试场景**
   - Admin 无角色 → 访问受保护接口 → 403
   - Admin 有角色但无权限 → 403
   - Admin 有角色有权限 → 200
   - 超级管理员 → 任何接口 → 200

## 向后兼容性

- 现有的 Admin 登录、刷新、登出、获取个人信息接口保持不变
- 新增的管理接口是额外的端点
- `is_superuser=False` 的 Admin 默认没有任何权限，需要分配角色

## 未来扩展

如果需要给 Doctor 添加权限系统：
1. 创建 `doctor_roles`、`doctor_permissions` 表
2. 扩展 `create_auth_dependency` 支持 Doctor 模型
3. 复用相同的权限检查逻辑
