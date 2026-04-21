from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    # 如果还有其他应用，可以在这里添加
    # path('inventory/', include('inventory.urls')),
]