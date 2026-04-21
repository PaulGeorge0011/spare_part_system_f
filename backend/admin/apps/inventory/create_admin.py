import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spare_part_admin.settings')
django.setup()

from django.contrib.auth.models import User

# 创建超级用户（如果不存在）
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='06002336fwbSQL'  # 在生产环境中使用环境变量
    )
    print("超级用户创建成功：admin / 06002336fwbSQL")
else:
    print("超级用户已存在")