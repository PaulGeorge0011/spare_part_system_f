from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SparePart, InventoryTransaction

@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ('location_code', 'mes_material_code', 'mes_material_desc', 
                    'specification_model', 'applicable_model', 'brand',
                    'display_mes_stock', 'display_physical_stock', 
                    'display_stock_difference', 'display_stock_status',
                    'storage_location', 'created_at')
    
    list_filter = ('location_code', 'brand', 'created_at')
    search_fields = ('location_code', 'mes_material_code', 'mes_material_desc',
                     'specification_model', 'applicable_model', 'brand')
    list_per_page = 50
    ordering = ('location_code', 'mes_material_code')
    
    # 只读字段（因为 managed=False）
    readonly_fields = ('id', 'created_at', 'updated_at', 'stock_difference', 'stock_status')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('location_code', 'mes_material_code', 'mes_material_desc')
        }),
        ('物料描述', {
            'fields': ('physical_material_desc', 'specification_model', 
                      'applicable_model', 'brand')
        }),
        ('库存信息', {
            'fields': ('mes_stock', 'physical_stock', 'unit', 'storage_location')
        }),
        ('图片信息', {
            'fields': ('physical_image_url', 'physical_image_url2'),
            'classes': ('collapse',)  # 可折叠
        }),
        ('其他信息', {
            'fields': ('remarks', 'created_at', 'updated_at')
        }),
    )
    
    def display_mes_stock(self, obj):
        if obj.mes_stock is None:
            return '-'
        return f"{obj.mes_stock} {obj.unit or ''}"
    display_mes_stock.short_description = 'MES库存'
    
    def display_physical_stock(self, obj):
        if obj.physical_stock is None:
            return '-'
        return f"{obj.physical_stock} {obj.unit or ''}"
    display_physical_stock.short_description = '实物库存'
    
    def display_stock_difference(self, obj):
        diff = obj.stock_difference
        if diff is None:
            return '-'
        
        if diff > 0:
            color = 'green'
            sign = '+'
        elif diff < 0:
            color = 'red'
            sign = ''
        else:
            color = 'blue'
            sign = ''
        
        return format_html(
            '<span style="color: {};">{}{} {}</span>',
            color, sign, diff, obj.unit or ''
        )
    display_stock_difference.short_description = '库存差异'
    
    def display_stock_status(self, obj):
        status = obj.stock_status
        color_map = {
            '缺货': 'red',
            '低库存': 'orange',
            '正常': 'green',
            '未知': 'gray'
        }
        color = color_map.get(status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    display_stock_status.short_description = '库存状态'
    
    def view_images(self, obj):
        """查看图片链接"""
        links = []
        if obj.physical_image_url:
            links.append(f'<a href="{obj.physical_image_url}" target="_blank">图片1</a>')
        if obj.physical_image_url2:
            links.append(f'<a href="{obj.physical_image_url2}" target="_blank">图片2</a>')
        
        if links:
            return mark_safe(' | '.join(links))
        return '-'
    view_images.short_description = '图片'
    
    # 添加自定义操作
    actions = ['export_selected', 'update_stock_info']
    
    def export_selected(self, request, queryset):
        """导出选中的备件信息"""
        # 这里可以添加导出逻辑
        from django.http import HttpResponse
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="spare_parts.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['位置代码', 'MES物料编码', '物料描述', '规格型号', 'MES库存', '实物库存', '库存差异'])
        
        for obj in queryset:
            writer.writerow([
                obj.location_code,
                obj.mes_material_code,
                obj.mes_material_desc or '',
                obj.specification_model or '',
                obj.mes_stock or '',
                obj.physical_stock or '',
                obj.stock_difference or ''
            ])
        
        return response
    export_selected.short_description = "导出选中备件"
    
    def update_stock_info(self, request, queryset):
        """批量更新库存信息（示例）"""
        # 这里可以添加实际的库存更新逻辑
        for obj in queryset:
            # 示例：记录需要更新的对象
            pass
        self.message_user(request, f"已标记 {queryset.count()} 个备件需要更新库存信息")
    update_stock_info.short_description = "更新库存信息"

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'get_spare_part_code', 'transaction_type',
                    'quantity_before', 'quantity_change', 'quantity_after',
                    'operator', 'reference_doc')
    
    list_filter = ('transaction_type', 'operator', 'transaction_date')
    search_fields = ('spare_part__mes_material_code', 'spare_part__mes_material_desc',
                     'operator', 'reference_doc')
    list_per_page = 50
    ordering = ('-transaction_date',)
    date_hierarchy = 'transaction_date'
    
    def get_spare_part_code(self, obj):
        return obj.spare_part.mes_material_code
    get_spare_part_code.short_description = '物料编码'
    
    # 允许通过物料编码搜索备件
    raw_id_fields = ('spare_part',)