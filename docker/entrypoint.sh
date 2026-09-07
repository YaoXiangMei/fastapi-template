#!/usr/bin/env bash
set -e

echo "正在等待 PostgreSQL..."
while ! pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL 已就绪！"

echo "正在等待 Redis..."
while ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; do
  sleep 1
done
echo "Redis 已就绪！"

echo "正在执行 Alembic 迁移..."
alembic upgrade head

echo "启动命令：$@"
exec "$@"
