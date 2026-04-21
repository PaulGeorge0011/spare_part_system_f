# api/v1/__init__.py
# 不在包初始化时导入 auth/inventory/wechat，由 main 按需导入，避免任一模块报错导致全部路由注册失败。
