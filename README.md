# FastAPI 模板

一个综合的 FastAPI 模板，集成异步 SQLAlchemy、pgvector、RBAC、Celery、Redis 等。

## 特性

- **FastAPI** —— 异步 Uvicorn，OpenAPI 文档位于 `/docs` 和 `/redoc`
- **SQLAlchemy 2.0** —— 使用 `asyncpg` 驱动的异步 ORM
- **pgvector** —— 向量相似度搜索（余弦距离）
- **Alembic** —— 异步数据库迁移（自动创建 `pgvector` 扩展）
- **JWT 认证** —— 访问令牌 + 通过 Redis 实现的刷新令牌轮换
- **RBAC** —— 用户、角色、权限，配合 `require_permission()` 依赖项
- **Redis** —— 连接池、缓存、限流、令牌存储
- **Celery** —— 带 beat 调度器的异步任务队列
- **统一响应格式** —— 所有响应包装为 `{code, message, data}`
- **分页** —— 可复用的 `PageData[T]` 响应模式
- **限流** —— Redis 固定窗口限流器
- **日志** —— 结构化 loguru 日志，带请求 ID 追踪
- **监控** —— Prometheus 指标位于 `/metrics`，健康检查位于 `/health/live` 和 `/health/ready`
- **Sentry** —— 可选的错误追踪（通过 `SENTRY_DSN` 启用）
- **Docker** —— 多阶段 Dockerfile，完整的 `docker-compose`（包含 Postgres + Redis + API + Worker + Beat）
- **测试** —— pytest + pytest-asyncio + httpx + fakeredis
- **CI** —— GitHub Actions，使用 ruff + mypy + pytest
- **uv** —— 快速依赖管理

## 技术栈

| 领域        | 技术                      |
|-------------|---------------------------|
| Web         | FastAPI, Uvicorn          |
| ORM         | SQLAlchemy 2.0（异步）     |
| 数据库      | PostgreSQL 16 + pgvector  |
| 迁移        | Alembic（异步环境）       |
| 缓存/限流   | Redis (redis.asyncio)     |
| 任务队列    | Celery + Redis broker     |
| 认证        | PyJWT + pwdlib (argon2)   |
| 配置        | pydantic-settings         |
| 日志        | loguru                    |
| 指标        | prometheus-fastapi        |
| 测试        | pytest, httpx, fakeredis  |
| 代码检查    | ruff, mypy                |
| 打包        | uv                        |
| Python      | >=3.12                    |

## 快速开始

### 使用 Docker（推荐）

```bash
# 1. 复制环境变量文件
cp .env.example .env

# 2. 启动所有服务
docker compose up -d --build

# 3. 运行迁移（入口脚本会自动执行此操作）
# 4. 初始化超级用户
docker compose exec api python -m app.scripts.seed

# 5. 访问文档
open http://localhost:8000/docs
```

### 本地开发

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装依赖
uv sync

# 复制环境变量文件
cp .env.example .env

# 启动 Postgres + Redis（或使用 docker compose up postgres redis）

# 运行迁移
uv run alembic upgrade head

# 初始化数据
uv run python -m app.scripts.seed

# 启动 API
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery worker（单独终端）
uv run celery -A app.worker.celery_app worker --loglevel=info

# 启动 Celery beat（单独终端，可选）
uv run celery -A app.worker.celery_app beat --loglevel=info
```

## 项目结构

```
app/
├── main.py              # FastAPI 应用工厂、生命周期、路由注册
├── api/
│   ├── router.py        # /api/v1 路由聚合
│   └── deps.py          # 共享依赖项（认证、数据库、Redis）
├── core/
│   ├── config.py        # 配置（pydantic-settings）
│   ├── database.py      # 异步引擎、会话、Base、混入
│   ├── redis.py         # Redis 连接池
│   ├── security.py      # JWT、密码哈希
│   ├── exceptions.py    # AppException 异常层级 + 处理器
│   ├── response.py      # 统一 ApiResponse 包装器
│   ├── logging.py       # loguru 配置
│   ├── middleware.py    # 请求 ID + 访问日志
│   ├── rate_limit.py    # Redis 限流器
│   ├── pagination.py    # 分页参数 + PageData 模式
│   └── metrics.py       # Prometheus 监控埋点
├── modules/
│   ├── auth/            # 注册、登录、刷新、登出
│   ├── user/            # 用户、角色、权限（RBAC）
│   └── vector/          # 带 pgvector 嵌入的文档
├── worker/              # Celery 应用 + 任务
└── scripts/             # 种子脚本
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

错误响应遵循相同格式，status 固定为 0（具体错误类型由 HTTP 状态码区分）：

```json
{
  "status": 0,
  "message": "User not found",
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

### 认证（`/api/v1/auth`）
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/register` | 注册新用户 |
| POST | `/login` | 登录（OAuth2 表单） |
| POST | `/refresh` | 轮换刷新令牌 |
| POST | `/logout` | 吊销刷新令牌 |

### 用户（`/api/v1/users`）
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/me` | 获取当前用户 |
| GET | `` | 列出用户（超级用户） |
| POST | `` | 创建用户（超级用户） |
| PATCH | `/{id}` | 更新用户（超级用户） |
| POST | `/{id}/roles` | 分配角色（超级用户） |

### 角色（`/api/v1/roles`）
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `` | 列出角色 |
| POST | `` | 创建角色（超级用户） |
| DELETE | `/{id}` | 删除角色（超级用户） |

### 权限（`/api/v1/permissions`）
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `` | 列出权限 |

### 文档（`/api/v1/documents`）
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `` | 创建文档（自动嵌入） |
| GET | `` | 列出文档 |
| GET | `/{id}` | 获取文档 |
| DELETE | `/{id}` | 删除文档 |
| POST | `/search` | 语义相似度搜索 |

### 健康检查
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health/live` | 存活探针 |
| GET | `/health/ready` | 就绪探针（数据库 + Redis） |
| GET | `/metrics` | Prometheus 指标 |

## 测试

```bash
# 确保 Postgres + Redis 正在运行
# 创建测试数据库
createdb fastapi_template_test

# 运行测试
uv run pytest -v

# 运行测试并生成覆盖率报告
uv run pytest --cov=app --cov-report=term-missing
```

## 代码质量

```bash
# 代码检查
uv run ruff check app tests

# 代码格式化
uv run ruff format app tests

# 类型检查
uv run mypy app
```

## 许可证

MIT
