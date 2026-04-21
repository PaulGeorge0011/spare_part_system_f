from django.core.management.base import BaseCommand
from django.db import connection
from inventory.models import SparePart
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '从数据库同步备件数据到 Django 模型'
    
    def handle(self, *args, **options):
        """同步现有数据到 Django ORM"""
        self.stdout.write('开始同步备件数据...')
        
        try:
            # 检查表是否存在
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE 'spare_parts'")
                table_exists = cursor.fetchone()
                
                if not table_exists:
                    self.stderr.write('错误: spare_parts 表不存在')
                    return
                
                # 获取总记录数
                cursor.execute("SELECT COUNT(*) FROM spare_parts")
                total_count = cursor.fetchone()[0]
                
                self.stdout.write(f'数据库中总记录数: {total_count}')
                
                # 检查 Django 模型中的记录数
                django_count = SparePart.objects.count()
                self.stdout.write(f'Django 模型中记录数: {django_count}')
                
                if django_count == total_count:
                    self.stdout.write(self.style.SUCCESS('数据已同步'))
                else:
                    self.stdout.write('数据可能需要同步，但模型设置为 managed=False')
                    
        except Exception as e:
            logger.error(f"同步数据时出错: {e}")
            self.stderr.write(f'错误: {e}')