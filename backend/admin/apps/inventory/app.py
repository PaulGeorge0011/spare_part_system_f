from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'  # 注意这里只是 'inventory'，不是 'apps.inventory'
    verbose_name = '库存管理'