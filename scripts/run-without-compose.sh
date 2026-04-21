#!/bin/bash
# 备件管理系统 — 无 Docker Compose 时使用纯 Docker 启动全部服务
# 使用前：在项目根目录执行，并确保已配置 .env（脚本会读取当前 shell 中已 export 的变量，未设置则用下方默认值）

set -e
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

# 若存在 .env，尝试加载（仅支持 KEY=VALUE 单行，无空格；复杂值请先 export 到环境）
if [ -f .env ]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "${line// }" ]] && continue
    export "$line" 2>/dev/null || true
  done < .env
fi

# 默认值（与 docker-compose.yml 一致）
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-06002336fwbSQL}"
MYSQL_USER="${MYSQL_USER:-sparepart}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-sparepart123}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-admin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-06002336fwbMINIO}"
SECRET_KEY="${SECRET_KEY:-dev-secret-key-change-in-production}"
DEBUG="${DEBUG:-False}"
NETWORK="spare-part-network"

echo "创建网络与卷..."
docker network create "$NETWORK" 2>/dev/null || true
docker volume create mysql_data 2>/dev/null || true
docker volume create redis_data 2>/dev/null || true
docker volume create minio_data 2>/dev/null || true
docker volume create django_static 2>/dev/null || true
docker volume create django_media 2>/dev/null || true

echo "启动 MySQL..."
docker run -d --name spare-part-mysql --network "$NETWORK" \
  -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  -e MYSQL_DATABASE=spare_part_db \
  -e MYSQL_USER="$MYSQL_USER" \
  -e MYSQL_PASSWORD="$MYSQL_PASSWORD" \
  -v mysql_data:/var/lib/mysql \
  -p 3307:3306 \
  --restart unless-stopped \
  mysql:8.0

echo "等待 MySQL 就绪..."
until docker exec spare-part-mysql mysqladmin ping -h localhost --silent 2>/dev/null; do sleep 2; done

echo "启动 Redis..."
docker run -d --name spare-part-redis --network "$NETWORK" \
  -v redis_data:/data -p 6379:6379 --restart unless-stopped redis:7-alpine

echo "启动 MinIO（Nginx 通过别名 minio 访问）..."
docker run -d --name spare-part-minio --network "$NETWORK" --network-alias minio \
  -e MINIO_ROOT_USER="$MINIO_ROOT_USER" \
  -e MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD" \
  -v minio_data:/data -p 9000:9000 -p 9001:9001 \
  --restart unless-stopped \
  minio/minio:latest server /data --console-address ":9001"

echo "等待 MinIO 就绪..."
sleep 5
docker run --rm --network "$NETWORK" \
  -e MINIO_ROOT_USER="$MINIO_ROOT_USER" \
  -e MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD" \
  minio/mc:latest /bin/sh -c "
    mc alias set myminio http://spare-part-minio:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD;
    mc mb myminio/spareparts --ignore-existing;
    mc policy set public myminio/spareparts;
  "

echo "构建并启动 FastAPI（Nginx 通过别名 fastapi 访问）..."
docker build -t spare-part-fastapi:local "$PROJECT_ROOT/backend/api"
docker run -d --name spare-part-fastapi --network "$NETWORK" --network-alias fastapi \
  -e DATABASE_URL="mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@spare-part-mysql:3306/spare_part_db" \
  -e REDIS_URL=redis://spare-part-redis:6379/0 \
  -e SECRET_KEY="$SECRET_KEY" \
  -e DEBUG="$DEBUG" \
  -e MINIO_ENDPOINT=spare-part-minio:9000 \
  -e MINIO_ACCESS_KEY="$MINIO_ROOT_USER" \
  -e MINIO_SECRET_KEY="$MINIO_ROOT_PASSWORD" \
  -e MINIO_BUCKET_NAME=spareparts \
  -e MINIO_SECURE=false \
  -v "$PROJECT_ROOT/backend/api:/app" \
  -v "$PROJECT_ROOT/uploads:/app/uploads" \
  -p 8888:8000 --restart unless-stopped \
  spare-part-fastapi:local uvicorn app.main:app --host 0.0.0.0 --port 8000

echo "构建并启动 Celery Worker..."
docker build -t spare-part-celery:local "$PROJECT_ROOT/backend/celery_worker"
docker run -d --name spare-part-celery-worker --network "$NETWORK" \
  -e DATABASE_URL="mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@spare-part-mysql:3306/spare_part_db" \
  -e REDIS_URL=redis://spare-part-redis:6379/0 \
  -v "$PROJECT_ROOT/backend/api:/app" \
  --restart unless-stopped \
  spare-part-celery:local celery -A app.celery_app worker --loglevel=info

echo "构建并启动 Frontend（Nginx 通过别名 frontend 访问）..."
docker build -t spare-part-frontend:local \
  --build-arg VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api/v1}" \
  "$PROJECT_ROOT/frontend"
docker run -d --name spare-part-frontend --network "$NETWORK" --network-alias frontend \
  -p 3000:80 --restart unless-stopped spare-part-frontend:local

echo "构建并启动 Django Admin（Nginx 通过别名 django-admin 访问，可选）..."
docker build -t spare-part-django-admin:local "$PROJECT_ROOT/backend/admin" 2>/dev/null || true
docker run -d --name spare-part-django-admin --network "$NETWORK" --network-alias django-admin \
  -e MYSQL_HOST=spare-part-mysql \
  -e MYSQL_DATABASE=spare_part_db \
  -e MYSQL_USER="$MYSQL_USER" \
  -e MYSQL_PASSWORD="$MYSQL_PASSWORD" \
  -v "$PROJECT_ROOT/backend/admin:/app" \
  -v django_static:/app/staticfiles \
  -v django_media:/app/media \
  -p 8001:8001 --restart unless-stopped \
  spare-part-django-admin:local \
  sh -c "sleep 10 && python manage.py migrate && python manage.py collectstatic --noinput && python manage.py createsuperuser --noinput || true && python manage.py runserver 0.0.0.0:8001" 2>/dev/null || true

echo "启动 Nginx..."
mkdir -p "$PROJECT_ROOT/nginx/conf.d" "$PROJECT_ROOT/nginx/ssl"
docker run -d --name spare-part-nginx --network "$NETWORK" \
  -p 80:80 -p 443:443 \
  -v "$PROJECT_ROOT/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$PROJECT_ROOT/nginx/conf.d:/etc/nginx/conf.d:ro" \
  -v "$PROJECT_ROOT/nginx/ssl:/etc/nginx/ssl:ro" \
  --restart unless-stopped nginx:alpine

echo "全部服务已启动。查看： docker ps"
