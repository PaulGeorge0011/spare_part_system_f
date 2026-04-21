# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token, decode_setup_token
from app.crud.user import get_user_by_username, get_user_by_id, create_user, update_user_password
from app.models.user import User
import json
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
    ChangePasswordFromLoginRequest,
    SetPasswordByTokenRequest,
)

router = APIRouter()
security = HTTPBearer(auto_error=False)


# 角色与物资范围：admin 全部；electrical_* 仅电气；mechanical_* 仅机械；requisition_clerk 兼容视为电气；general_staff 无电气/机械范围
ROLES_ELECTRICAL = {"admin", "electrical_admin", "electrical_requisition_clerk", "requisition_clerk"}
ROLES_MECHANICAL = {"admin", "mechanical_admin", "mechanical_requisition_clerk"}
ALL_ROLES = {"admin", "electrical_requisition_clerk", "mechanical_requisition_clerk", "electrical_admin", "mechanical_admin", "general_staff"}


def _user_material_scopes(user: User) -> list[str]:
    """
    按角色计算物资范围。
    - 角色用户（electrical_admin 等）：由角色直接推导。
    - general_staff：从 permissions JSON 列读取 electrical / mechanical 键，有任意级别即有范围。
    """
    role = (getattr(user, "role", None) or "").strip()
    if role == "admin":
        return ["electrical", "mechanical"]
    if role in ("electrical_admin", "electrical_requisition_clerk", "requisition_clerk"):
        return ["electrical"]
    if role in ("mechanical_admin", "mechanical_requisition_clerk"):
        return ["mechanical"]
    if role == "general_staff":
        raw = getattr(user, "permissions", None) or ""
        try:
            perms: dict = json.loads(raw) if raw else {}
        except (ValueError, TypeError):
            perms = {}
        scopes = []
        if perms.get("electrical") in ("admin", "editor", "viewer"):
            scopes.append("electrical")
        if perms.get("mechanical") in ("admin", "editor", "viewer"):
            scopes.append("mechanical")
        return scopes
    scopes_raw = getattr(user, "material_scopes", None) or ""
    if scopes_raw.strip():
        allowed = [s.strip() for s in scopes_raw.split(",") if s.strip()]
        if allowed:
            return allowed
    return ["electrical", "mechanical"]


def require_material_scope(scope: str):
    """依赖：校验当前用户是否拥有指定物资范围（electrical / mechanical）。"""
    def _(current_user: User = Depends(get_current_user)) -> User:
        allowed = _user_material_scopes(current_user)
        if scope not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无该物资类型的访问权限",
            )
        return current_user
    return _


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证信息")
    decoded = decode_access_token(creds.credentials)
    if not decoded:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或过期的令牌")
    subject, token_version = decoded
    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    user_status = getattr(user, "status", "approved") or "approved"
    if user_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的账号待管理员审核，暂无法使用系统",
        )
    current_version = getattr(user, "token_version", 0) or 0
    if current_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="您的权限已变更，请重新登录",
        )
    return user


@router.get("/auth/test")
async def auth_test():
    return {"message": "认证模块已实现"}


@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    # req.username 已由 Pydantic 校验（长度、安全字符），且 get_user_by_username 使用 ORM 参数化查询，防 SQL 注入
    user = get_user_by_username(db, req.username)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    user_status = getattr(user, "status", "approved") or "approved"
    if user_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的账号待管理员审核，审核通过后方可登录",
        )
    version = getattr(user, "token_version", 0) or 0
    token = create_access_token(subject=user.id, token_version=version)
    material_scopes = _user_material_scopes(user)
    raw_perms = getattr(user, "permissions", None) or ""
    try:
        perms: dict = json.loads(raw_perms) if raw_perms else {}
    except (ValueError, TypeError):
        perms = {}
    return LoginResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            real_name=getattr(user, "real_name", None),
            role=user.role,
            material_scopes=material_scopes,
            permissions=perms,
        ),
    )


@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册。注册成功后需登录使用。"""
    if get_user_by_username(db, req.username.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    create_user(
        db,
        req.username.strip(),
        get_password_hash(req.password),
        role="requisition_clerk",
        status="pending",
        real_name=(req.real_name or "").strip() or None,
    )
    return RegisterResponse(message="注册成功，请等待管理员审核通过后再登录")


@router.get("/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    material_scopes = _user_material_scopes(current_user)
    raw_perms = getattr(current_user, "permissions", None) or ""
    try:
        perms: dict = json.loads(raw_perms) if raw_perms else {}
    except (ValueError, TypeError):
        perms = {}
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        real_name=getattr(current_user, "real_name", None),
        role=current_user.role,
        material_scopes=material_scopes,
        permissions=perms,
    )


@router.post("/auth/change-password", status_code=status.HTTP_200_OK)
async def change_password_from_login(req: ChangePasswordFromLoginRequest, db: Session = Depends(get_db)):
    """登录页修改密码：凭账号与旧密码验证后设置新密码，无需登录。"""
    user = get_user_by_username(db, req.username)
    if not user or not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或旧密码错误")
    user_status = getattr(user, "status", "approved") or "approved"
    if user_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的账号待管理员审核，暂无法修改密码",
        )
    if not update_user_password(db, user.id, get_password_hash(req.new_password)):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="修改失败")
    return {"message": "密码已修改，请使用新密码登录"}


@router.post("/auth/set-password-by-token", status_code=status.HTTP_200_OK)
async def set_password_by_token(req: SetPasswordByTokenRequest, db: Session = Depends(get_db)):
    """通过设置密码链接中的 token 设置新密码（无需登录）。用于管理员新建用户后，用户通过链接自助设置密码。"""
    user_id = decode_setup_token(req.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="链接无效或已过期，请联系管理员重新发送设置密码链接",
        )
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not update_user_password(db, user.id, get_password_hash(req.new_password)):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="设置失败")
    return {"message": "密码设置成功，请使用新密码登录"}
