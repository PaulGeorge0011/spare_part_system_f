"""
统一模块权限工具
- 所有模块（含 electrical / mechanical）均支持 User.permissions JSON 列配置
- 现有角色用户（electrical_admin 等）通过 _user_material_scopes 自动推导等效级别，无需迁移
- 新模块路由使用：Depends(require_module_permission("process", "editor"))
"""
import json
from typing import Optional

from fastapi import Depends, HTTPException, status

# 权限级别顺序
_LEVEL_ORDER: dict[str, int] = {"viewer": 1, "editor": 2, "admin": 3}

# 旧版模块 ID：已清空，所有模块均支持 permissions 列配置（保留变量供外部引用，避免 ImportError）
LEGACY_MODULE_IDS: set[str] = set()

# 模块管理员授权规则：角色 → { modules: 可管理的模块集合, max_level: 可授予的最高级别 }
# 防越权原则：模块管理员只能授予低于自身的级别（editor 及以下），超级管理员才能授 admin
MANAGED_MODULES: dict[str, dict] = {
    "electrical_admin": {
        "modules": {"electrical"},
        "max_level": "editor",
    },
    "mechanical_admin": {
        "modules": {"mechanical"},
        "max_level": "editor",
    },
}


def has_level(user_level: Optional[str], required: str) -> bool:
    """检查 user_level 是否满足 required 的最低要求"""
    if not user_level:
        return False
    return _LEVEL_ORDER.get(user_level, 0) >= _LEVEL_ORDER.get(required, 0)


def get_user_module_permissions(user) -> dict[str, str]:
    """从 User.permissions 列解析模块权限字典"""
    raw = getattr(user, "permissions", None)
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


def get_module_permission_level(user, module: str) -> Optional[str]:
    """获取用户对指定模块的权限级别"""
    return get_user_module_permissions(user).get(module)


def require_module_permission(module: str, level: str = "viewer"):
    """
    新模块路由权限校验依赖工厂（主要用于 process / safety 等纯新模块）。
    electrical / mechanical 的 API 路由由 require_material_scope 保护，
    但本函数也能正确处理拥有对应 permissions 的 general_staff 用户。
    """
    from ..api.v1.auth import get_current_user

    def _(current_user=Depends(get_current_user)):
        # 超级管理员始终有权限
        if getattr(current_user, "role", None) == "admin":
            return current_user
        user_level = get_module_permission_level(current_user, module)
        if not has_level(user_level, level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"无 {module} 模块访问权限（需要 {level} 级别）",
            )
        return current_user

    return _


# 合法的可配置权限级别（只读 / 可编辑，admin 级别由角色决定，不可通过模块权限接口设置）
VALID_PERM_LEVELS = {"editor", "viewer"}
