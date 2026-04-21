# app/schemas/auth.py
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from ..core.datetime_utils import ensure_utc_aware

# 登录用户名：仅允许字母、数字、下划线、中文，长度 1～64，防止 SQL 注入与异常输入
USERNAME_SAFE_PATTERN = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fa5]{1,64}$")
# 拒绝的 SQL 危险字符（双重防护）
SQL_UNSAFE_RE = re.compile(r"[\s'\"\\;]|--|/\*|\*/")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=72, description="密码（bcrypt 上限 72 字节）")

    @field_validator("username", mode="before")
    @classmethod
    def username_strip_and_validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("用户名必须为字符串")
        s = v.strip()
        if not s:
            raise ValueError("用户名不能为空")
        if len(s) > 64:
            raise ValueError("用户名长度不能超过 64 个字符")
        if SQL_UNSAFE_RE.search(s):
            raise ValueError("用户名包含非法字符")
        if not USERNAME_SAFE_PATTERN.match(s):
            raise ValueError("用户名仅允许字母、数字、下划线或中文")
        return s

    @field_validator("password", mode="before")
    @classmethod
    def password_validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("密码必须为字符串")
        if len(v) > 72:
            raise ValueError("密码长度不能超过 72 个字符")
        return v


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    real_name: str = Field(..., min_length=1, max_length=100, description="真实姓名")
    password: str = Field(..., min_length=6, max_length=72, description="密码")


class UserResponse(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    role: str
    material_scopes: list[str] = []  # 前端用 scopes：['electrical'], ['mechanical'], ['electrical','mechanical']
    permissions: dict[str, str] = {}  # 新模块权限：{"process": "admin", "safety": "viewer"}

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    role: str
    material_scopes: list[str] = []  # 物资范围：electrical, mechanical 等
    status: str = "approved"
    wechat_userid: Optional[str] = None
    wechat_name: Optional[str] = None
    permissions: dict[str, str] = {}  # 新模块权限
    created_at: Optional[datetime] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_utc_aware(cls, v):
        return ensure_utc_aware(v) if v is not None else v

    class Config:
        from_attributes = True


VALID_ROLES = (
    "admin",
    "electrical_requisition_clerk",
    "mechanical_requisition_clerk",
    "electrical_admin",
    "mechanical_admin",
    "general_staff",   # 通用人员：不属于电气/机械，权限完全由 permissions 列控制
)


class UserUpdatePermissionsRequest(BaseModel):
    """更新用户新模块权限（仅超级管理员可调用）"""
    permissions: dict[str, str] = Field(
        default={},
        description="模块权限字典，key 为模块 ID，value 为 admin/editor/viewer；传空字典则清空所有新模块权限",
    )


class UserUpdateRoleRequest(BaseModel):
    role: str = Field(..., description="电气领用员/机械领用员/电气管理员/机械管理员/通用人员/admin")


class UserApproveRequest(BaseModel):
    role: str = Field(..., description="审批通过时的角色：电气领用员/机械领用员/电气管理员/机械管理员/通用人员/admin")
    permissions: dict[str, str] = Field(
        default={},
        description="审批为通用人员时同步设置的初始模块权限（可选）",
    )


class AdminCreateUserRequest(BaseModel):
    """管理员新建用户（授权分级：超级管理员任意角色与权限，模块管理员仅能创建本模块领用员或通用人员且权限不超过 editor）"""
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    real_name: Optional[str] = Field(None, max_length=100, description="真实姓名")
    role: str = Field(..., description="角色")
    permissions: dict[str, str] = Field(
        default={},
        description="模块权限（仅当 role=general_staff 时有效；模块管理员仅能配置其管辖模块且最高 editor）",
    )


class AdminCreateUserResponse(BaseModel):
    username: str
    real_name: Optional[str] = None
    token: str = Field(..., description="设置密码链接用 token，7 天内有效")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterResponse(BaseModel):
    message: str = "注册成功，请登录"


class SetPasswordByTokenRequest(BaseModel):
    """通过设置密码链接 token 设置新密码（无需登录）"""
    token: str = Field(..., min_length=1, description="设置密码链接中的 token")
    new_password: str = Field(..., min_length=6, max_length=72, description="新密码，至少 6 位")

    @field_validator("new_password", mode="before")
    @classmethod
    def password_validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("密码必须为字符串")
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        if len(v) > 72:
            raise ValueError("密码长度不能超过 72 个字符")
        return v


class ChangePasswordRequest(BaseModel):
    """已登录用户修改密码"""
    current_password: str = Field(..., min_length=1, max_length=72)
    new_password: str = Field(..., min_length=6, max_length=72)

    @field_validator("new_password", mode="before")
    @classmethod
    def new_password_validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("新密码必须为字符串")
        if len(v) < 6:
            raise ValueError("新密码至少 6 位")
        if len(v) > 72:
            raise ValueError("新密码长度不能超过 72 个字符")
        return v


class ChangePasswordFromLoginRequest(BaseModel):
    """登录页修改密码：账号 + 旧密码 + 新密码（无需登录）"""
    username: str = Field(..., min_length=1, max_length=64, description="账号")
    old_password: str = Field(..., min_length=1, max_length=72, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=72, description="新密码")

    @field_validator("username", mode="before")
    @classmethod
    def username_strip_and_validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("账号必须为字符串")
        s = v.strip()
        if not s:
            raise ValueError("账号不能为空")
        if len(s) > 64:
            raise ValueError("账号长度不能超过 64 个字符")
        if SQL_UNSAFE_RE.search(s):
            raise ValueError("账号包含非法字符")
        if not USERNAME_SAFE_PATTERN.match(s):
            raise ValueError("账号仅允许字母、数字、下划线或中文")
        return s

    @field_validator("new_password", mode="before")
    @classmethod
    def new_password_validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("新密码必须为字符串")
        if len(v) < 6:
            raise ValueError("新密码至少 6 位")
        if len(v) > 72:
            raise ValueError("新密码长度不能超过 72 个字符")
        return v
