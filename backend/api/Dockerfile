# backend/api/Dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制当前目录（backend/api）下的requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制当前目录（backend/api）下的所有文件
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]