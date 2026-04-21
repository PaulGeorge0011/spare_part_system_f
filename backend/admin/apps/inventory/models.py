from django.db import models

class SparePart(models.Model):
    id = models.AutoField(primary_key=True)
    location_code = models.CharField(max_length=50, verbose_name='位置代码')
    mes_material_code = models.CharField(max_length=100, unique=True, verbose_name='MES物料编码')
    mes_material_desc = models.CharField(max_length=255, blank=True, null=True, verbose_name='MES物料描述')
    physical_material_desc = models.TextField(blank=True, null=True, verbose_name='实物物料描述')
    specification_model = models.CharField(max_length=255, blank=True, null=True, verbose_name='规格型号')
    applicable_model = models.CharField(max_length=255, blank=True, null=True, verbose_name='适用机型')
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name='品牌')
    mes_stock = models.FloatField(blank=True, null=True, verbose_name='MES库存')
    physical_stock = models.FloatField(blank=True, null=True, verbose_name='实物库存')
    unit = models.CharField(max_length=20, blank=True, null=True, verbose_name='单位')
    remarks = models.TextField(blank=True, null=True, verbose_name='备注')
    storage_location = models.CharField(max_length=255, blank=True, null=True, verbose_name='存放位置')
    physical_image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='实物图片URL')
    physical_image_url2 = models.URLField(max_length=500, blank=True, null=True, verbose_name='实物图片URL2')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'spare_parts'  # 指定表名
        managed = False  # 设置为 False，因为表已存在且由 FastAPI 管理
        verbose_name = '备件'
        verbose_name_plural = '备件管理'
        ordering = ['location_code', 'mes_material_code']
    
    def __str__(self):
        return f"{self.location_code} - {self.mes_material_code}"
    
    @property
    def stock_difference(self):
        """计算库存差异"""
        if self.mes_stock is not None and self.physical_stock is not None:
            return round(self.physical_stock - self.mes_stock, 2)
        return None
    
    @property
    def stock_status(self):
        """库存状态"""
        if self.physical_stock is None:
            return '未知'
        if self.physical_stock <= 0:
            return '缺货'
        elif self.physical_stock < 10:  # 假设安全库存为10
            return '低库存'
        else:
            return '正常'



class InventoryTransaction(models.Model):
    """库存交易记录表"""
    TRANSACTION_TYPES = [
        ('IN', '入库'),
        ('OUT', '出库'),
        ('ADJUST', '调整'),
        ('COUNT', '盘点'),
    ]
    
    id = models.AutoField(primary_key=True)
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE, verbose_name='备件')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='交易类型')
    quantity_before = models.FloatField(verbose_name='交易前数量')
    quantity_change = models.FloatField(verbose_name='数量变化')
    quantity_after = models.FloatField(verbose_name='交易后数量')
    operator = models.CharField(max_length=100, verbose_name='操作员')
    transaction_date = models.DateTimeField(auto_now_add=True, verbose_name='交易时间')
    remark = models.TextField(blank=True, null=True, verbose_name='备注')
    reference_doc = models.CharField(max_length=100, blank=True, null=True, verbose_name='参考单据')
    
    class Meta:
        db_table = 'inventory_transactions'
        managed = True  # 如果表已存在，设置为 False
        # managed = True  # 如果表不存在，让 Django 创建表
        verbose_name = '库存交易'
        verbose_name_plural = '库存交易记录'
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.spare_part.mes_material_code}"