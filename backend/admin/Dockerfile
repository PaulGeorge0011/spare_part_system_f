FROM python:3.11-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建启动脚本
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# 设置 Python 路径\n\
export PYTHONPATH=/app:/app/apps\n\
export DJANGO_SETTINGS_MODULE=spare_part_admin.settings\n\
\n\
echo "Waiting for MySQL..."\n\
sleep 10\n\
\n\
echo "Running migrations..."\n\
python manage.py migrate\n\
\n\
echo "Collecting static files..."\n\
python manage.py collectstatic --noinput\n\
\n\
echo "Creating superuser..."\n\
python manage.py createsuperuser --noinput --username admin --email admin@example.com --password admin123 2>/dev/null || echo "Superuser already exists or failed to create"\n\
\n\
echo "Starting Gunicorn..."\n\
exec gunicorn --bind 0.0.0.0:8001 --workers 3 spare_part_admin.wsgi:application\n\
' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]