#!/bin/bash
# 在有外网的机器上执行：拉取/构建镜像并导出为 tar，供工厂无外网服务器加载
# 使用：在项目根目录执行 bash scripts/save-images-for-offline.sh

set -e
cd "$(dirname "$0")/.."

echo "1. 拉取并构建镜像（需联网）..."
docker-compose pull
docker-compose build

echo "2. 获取镜像列表并导出..."
# 使用 docker-compose config --images 获取所有镜像名（含构建的），再导出
docker-compose config --images 2>/dev/null | sort -u | xargs docker save -o spare_part_images.tar || {
  # 回退：使用固定列表（项目目录名为 spare_part_system 时）
  PROJECT_NAME=$(basename "$(pwd)")
  echo "回退到固定镜像列表 (project=$PROJECT_NAME)"
  docker save -o spare_part_images.tar \
    minio/minio:latest minio/mc:latest mysql:8.0 redis:7-alpine nginx:alpine \
    "${PROJECT_NAME}-fastapi" "${PROJECT_NAME}-frontend" "${PROJECT_NAME}-celery-worker" "${PROJECT_NAME}-django-admin"
}

echo "3. 完成。请将 spare_part_images.tar 拷贝到工厂服务器，然后执行："
echo "   docker load -i spare_part_images.tar"
echo "   docker-compose up -d --no-build"
