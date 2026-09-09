# FastAPI 模板

一个综合的 FastAPI 模板，集成异步 SQLAlchemy、pgvector、多角色认证、Admin RBAC、Celery、Redis 等。

## 特性

- **FastAPI** —— 异步 Uvicorn，OpenAPI 文档位于 `/docs` 和 `/redoc`
- **SQLAlchemy 2.0** —— 使用 `asyncpg` 驱动的异步 ORM
- **pgvector** —— 向量相似度搜索（余弦距离）
- **Alembic** —— 异步数据库迁移（自动创建 `pgvector` 扩展）
- **多角色认证** —— Patient / Doctor / Admin 独立用户表，JWT + Redis 刷新令牌轮换
- **Admin RBAC** —— 权限 → 角色 → 管理员，`require_admin()` 细粒度权限控制
- **Redis** —— 连接池、缓存、限流、令牌存储
- **Celery** —— 带 beat 调度器的任务队列
- **统一响应格式** —— 所有响应包装为 `{status, message, data}`
- **分页** —— 可复用的 `PageData[T]` 响应模式
- **限流** —— Redis 固定窗口限流器
- **日志** —— 结构化 loguru 日志，带请求 ID 追踪
- **监控** —— Prometheus 指标位于 `/metrics`，健康检查位于 `/health/live` 和 `/health/ready`
- **Sentry** —— 可选的错误追踪（通过 `SENTRY_DSN` 启用）
- **Docker** —— 多阶段 Dockerfile，完整的 `docker-compose`（Postgres + Redis + API + Worker + Beat）
- **测试** —— pytest + pytest-asyncio + httpx + fakeredis
- **CI** —— GitHub Actions，ruff + mypy + pytest
- **代码规范** —— pre-commit hooks + ruff + mypy
- **uv** —— 快速依赖管理

## 技术栈

| 领域        | 技术                        |
|-------------|-----------------------------|
| Web         | FastAPI, Uvicorn            |
| ORM         | SQLAlchemy 2.0（异步）       |
| 数据库      | PostgreSQL 16 + pgvector    |
| 迁移        | Alembic（异步环境）         |
| 缓存/限流   | Redis (redis.asyncio)       |
| 任务队列    | Celery + Redis broker       |
| 认证        | PyJWT + pwdlib (argon2)     |
| 配置        | pydantic-settings           |
| 日志        | loguru                      |
| 指标        | prometheus-fastapi          |
| 测试        | pytest, httpx, fakeredis    |
| 代码检查    | ruff, mypy, pre-commit      |
| 打包        | uv                          |
| Python      | >=3.12                      |

## 快速开始

### 使用 Docker（推荐）

```bash
# 1. 复制 Docker 环境变量文件
cp .env.docker .env

# 2. 启动所有服务
docker compose up -d --build

# 3. 初始化数据（权限 + 管理员账号）
docker compose exec api python -m app.scripts.seed

# 4. 访问文档
open http://localhost:8000/docs
```

### 本地开发

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
make install

# 复制环境变量
cp .env.example .env

# 启动 Postgres + Redis
make docker-db-only

# 运行迁移
make migrate

# 初始化数据
make seed

# 启动 API
make dev

# 启动 Celery worker（单独终端）
make worker

# 启动 Celery beat（单独终端，可选）
make beat
```

### 使用 Makefile

```bash
make help            # 查看所有可用命令
make install         # 安装依赖
make dev             # 启动 API（热重载）
make test            # 运行测试
make lint            # 代码检查
make format          # 代码格式化
make migrate         # 数据库迁移
make seed            # 初始化数据
make docker-up       # 启动 Docker 全部服务
make docker-db-only  # 仅启动 PostgreSQL + Redis
make clean           # 清理缓存
```

## 项目结构

```
app/
├── main.py                  # FastAPI 应用工厂、生命周期、健康检查
├── api/
│   └── router.py            # /api/v1 路由聚合
├── core/
│   ├── auth_factory.py      # 通用 OAuth2 认证工厂（多角色）
│   ├── config.py            # 配置（pydantic-settings）
│   ├── database.py          # 异步引擎、会话、Base、混入
│   ├── redis.py             # Redis 连接池
│   ├── security.py          # JWT、密码哈希
│   ├── exceptions.py        # 异常层级 + 处理器
│   ├── response.py          # 统一 ApiResponse[T] 包装器
│   ├── schemas.py           # 共享 Schema（TokenResponse 等）
│   ├── logging.py           # loguru 配置
│   ├── middleware.py        # 请求 ID + 访问日志
│   ├── rate_limit.py        # Redis 限流器
│   ├── pagination.py        # 分页参数 + PageData[T]
│   └── metrics.py           # Prometheus 监控
├── modules/
│   ├── patient/             # 患者模块（注册、登录、刷新、登出、/me）
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── router.py
│   │   └── deps.py          # get_current_patient
│   ├── doctor/              # 医生模块（注册、登录、刷新、登出、/me）
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── deps.py          # get_current_doctor
│   │   └── management_router.py  # Admin 管理医生（审核、状态管理）
│   ├── admin/               # 管理员模块（登录、刷新、登出、/me）
│   │   ├── models.py        # Admin, AdminRole, AdminPermission
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── deps.py          # get_current_admin, require_admin()
│   │   ├── rbac_router.py   # RBAC 管理（权限/角色 CRUD、分配）
│   │   └── rbac_service.py  # RBAC 业务逻辑
│   └── vector/              # 文档向量模块（pgvector 嵌入 + 语义搜索）
│       ├── models.py
│       ├── schemas.py
│       ├── service.py
│       ├── router.py
│       └── embeddings.py    # 向量嵌入生成
├── worker/                  # Celery 应用 + 任务
│   ├── celery_app.py
│   └── tasks.py
└── scripts/
    └── seed.py              # 统一种子脚本（权限 + 管理员）
```

## 统一响应格式

所有 API 响应遵循以下结构：

```json
{
  "status": 1,
  "message": "success",
  "data": { ... }
}
```

错误响应（status 固定为 0，具体错误类型由 HTTP 状态码区分）：

```json
{
  "status": 0,
  "message": "Invalid email or password",
  "data": null
}
```

分页响应：

```json
{
  "status": 1,
  "message": "success",
  "data": {
    "data": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

## API 端点

### 患者（`/api/v1/patient`）
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/register` | 患者注册 |
| POST | `/login` | 患者登录（OAuth2 表单） |
| POST | `/refresh` | 刷新令牌 |
| POST | `/logout` | 登出（吊销刷新令牌） |
| GET | `/me` | 获取当前患者信息 |

### 医生（`/api/v1/doctor`）
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/register` | 医生注册（需审核） |
| POST | `/login` | 医生登录（OAuth2 表单） |
| POST | `/refresh` | 刷新令牌 |
| POST | `/logout` | 登出 |
| GET | `/me` | 获取当前医生信息 |

### 管理员（`/api/v1/admin`）
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/login` | 管理员登录（OAuth2 表单） |
| POST | `/refresh` | 刷新令牌 |
| POST | `/logout` | 登出 |
| GET | `/me` | 获取当前管理员信息 |

### Admin RBAC 管理（`/api/v1/admin`）
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/permissions` | 创建权限（超级管理员） |
| GET | `/permissions` | 列出所有权限 |
| POST | `/roles` | 创建角色（超级管理员） |
| GET | `/roles` | 列出所有角色 |
| POST | `/roles/{id}/permissions` | 给角色分配权限（超级管理员） |
| GET | `/users` | 列出所有管理员（超级管理员） |
| POST | `/users/{id}/roles` | 给管理员分配角色（超级管理员） |

### Admin 医生管理（`/api/v1/admin/doctors`）
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `` | 列出所有医生（管理员） |
| PATCH | `/{id}/approve` | 审核通过医生 |
| PATCH | `/{id}/status` | 启用/停用医生账号 |

### 文档（`/api/v1/documents`）
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `` | 创建文档（自动生成向量嵌入） |
| GET | `` | 列出文档（分页） |
| GET | `/{id}` | 获取文档 |
| DELETE | `/{id}` | 删除文档 |
| POST | `/search` | 语义相似度搜索 |

### 健康检查
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health/live` | 存活探针 |
| GET | `/health/ready` | 就绪探针（数据库 + Redis） |
| GET | `/metrics` | Prometheus 指标 |

## 使用示例

### 患者注册 & 登录

```bash
# 注册
curl -X POST http://localhost:8000/api/v1/patient/register \
  -H "Content-Type: application/json" \
  -d '{"email": "patient@example.com", "password": "password123", "full_name": "张三"}'

# 登录
curl -X POST http://localhost:8000/api/v1/patient/login \
  -d "username=patient@example.com&password=password123"

# 访问需要认证的接口
curl http://localhost:8000/api/v1/patient/me \
  -H "Authorization: Bearer <access_token>"
```

### 医生注册（需管理员审核）

```bash
# 注册（is_verified 默认为 false，需要管理员审核后才能登录）
curl -X POST http://localhost:8000/api/v1/doctor/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@example.com",
    "password": "password123",
    "full_name": "李医生",
    "license_no": "DOC-2024-001",
    "specialty": "内科"
  }'

# 管理员审核通过
curl -X PATCH http://localhost:8000/api/v1/admin/doctors/<doctor_id>/approve \
  -H "Authorization: Bearer <admin_token>"
```

### 管理员登录 & RBAC

```bash
# 管理员登录
curl -X POST http://localhost:8000/api/v1/admin/login \
  -d "username=admin&password=admin123456"

# 查看所有权限
curl http://localhost:8000/api/v1/admin/permissions \
  -H "Authorization: Bearer <admin_token>"

# 创建角色
curl -X POST http://localhost:8000/api/v1/admin/roles \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "运营管理员", "description": "负责日常运营"}'

# 给角色分配权限
curl -X POST http://localhost:8000/api/v1/admin/roles/<role_id>/permissions \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_ids": ["<perm_id_1>", "<perm_id_2>"]}'
```

### 文档 & 语义搜索

```bash
# 创建文档（自动生成向量嵌入）
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"title": "FastAPI Guide", "content": "FastAPI is a modern web framework for building APIs."}'

# 语义搜索
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "web framework guide", "top_k": 3}'
```

## 测试

```bash
# 运行测试
make test

# 运行测试并生成覆盖率报告
uv run pytest --cov=app --cov-report=term-missing
```

## 代码质量

```bash
# 代码检查
make lint

# 代码格式化
make format

# 安装 pre-commit hooks（推荐）
uv run pre-commit install
```

## 许可证

MIT — 详见 [LICENSE](LICENSE)
