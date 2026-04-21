# app/api/v1/sso.py
"""
SSO 单点登录接口（Keycloak OIDC）

支持两种授权方式：
1. 标准登录页（测试用）：跳转 Keycloak 登录页，输入账号密码
2. 企业微信免登录（生产用）：携带 kc_idp_hint=wechat-work，企业微信内免登录/PC 扫码
"""
import logging
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.crud.user import (
    get_user_by_sso_id,
    get_user_by_username,
    create_sso_user,
    bind_user_sso,
)
from app.models.user import User
from app.schemas.auth import LoginResponse, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------- 辅助：构造 Keycloak URL ----------

def _oidc_base() -> str:
    """Keycloak OIDC 端点基础路径"""
    return f"{settings.SSO_BASE_URL.rstrip('/')}/realms/{settings.SSO_REALM}/protocol/openid-connect"


def _build_auth_url(wechat: bool = False) -> str:
    """构造授权链接"""
    params = {
        "client_id": settings.SSO_CLIENT_ID,
        "redirect_uri": settings.SSO_REDIRECT_URI,
        "state": "",
        "response_type": "code",
        "scope": "openid email profile custom_scope",
    }
    if wechat:
        params["nonce"] = "NONCE"
        params["kc_idp_hint"] = "wechat-work"
    return f"{_oidc_base()}/auth?{urlencode(params, quote_via=quote)}"


# ---------- 角色与物资范围（复用 auth.py 的逻辑） ----------

def _user_material_scopes(user: User) -> list[str]:
    role = (getattr(user, "role", None) or "").strip()
    if role == "admin":
        return ["electrical", "mechanical"]
    if role in ("electrical_admin", "electrical_requisition_clerk", "requisition_clerk"):
        return ["electrical"]
    if role in ("mechanical_admin", "mechanical_requisition_clerk"):
        return ["mechanical"]
    scopes_raw = getattr(user, "material_scopes", None) or ""
    if scopes_raw.strip():
        return [s.strip() for s in scopes_raw.split(",") if s.strip()]
    return ["electrical", "mechanical"]


# ---------- 请求/响应模型 ----------

class SsoUrlResponse(BaseModel):
    url: str
    sso_enabled: bool = True


class SsoLoginRequest(BaseModel):
    code: str
    session_state: str = ""


class SsoStatusResponse(BaseModel):
    sso_enabled: bool


# ---------- 接口 ----------

@router.get("/auth/sso-status", response_model=SsoStatusResponse)
async def sso_status():
    """返回 SSO 是否启用（前端据此决定是否显示 SSO 登录入口）"""
    return SsoStatusResponse(sso_enabled=settings.SSO_ENABLED)


@router.get("/auth/sso-url", response_model=SsoUrlResponse)
async def get_sso_url(wechat: bool = Query(False, description="是否使用企业微信免登录")):
    """返回 SSO 授权链接，前端跳转到该链接进行登录"""
    if not settings.SSO_ENABLED:
        raise HTTPException(status_code=400, detail="SSO 未启用")
    if not settings.SSO_CLIENT_ID or not settings.SSO_BASE_URL:
        raise HTTPException(status_code=500, detail="SSO 配置不完整")
    url = _build_auth_url(wechat=wechat)
    return SsoUrlResponse(url=url)


@router.post("/auth/sso-login", response_model=LoginResponse)
async def sso_login(req: SsoLoginRequest, db: Session = Depends(get_db)):
    """
    用 SSO 授权 code 换取用户信息，匹配或创建本系统用户，签发本系统 JWT。

    流程：
    1. code → Keycloak token 接口换 access_token
    2. access_token → Keycloak userinfo 接口获取用户信息
    3. 用 user_id（工号）匹配本系统 users 表
    4. 签发本系统 JWT 并返回
    """
    if not settings.SSO_ENABLED:
        raise HTTPException(status_code=400, detail="SSO 未启用")

    # ---- Step 1: code 换 access_token ----
    token_url = f"{_oidc_base()}/token"
    token_data = {
        "client_id": settings.SSO_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": req.code,
        "client_secret": settings.SSO_CLIENT_SECRET,
        "redirect_uri": settings.SSO_REDIRECT_URI,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(token_url, data=token_data)
    except Exception as e:
        logger.error("SSO token 请求失败: %s", e)
        raise HTTPException(status_code=502, detail=f"SSO 服务连接失败: {e}")

    if token_resp.status_code != 200:
        logger.error("SSO token 响应异常: %s %s", token_resp.status_code, token_resp.text)
        raise HTTPException(
            status_code=401,
            detail=f"SSO 授权码无效或已过期（{token_resp.status_code}）",
        )

    token_json = token_resp.json()
    sso_access_token = token_json.get("access_token")
    if not sso_access_token:
        raise HTTPException(status_code=502, detail="SSO 未返回 access_token")

    # ---- Step 2: 获取用户信息 ----
    userinfo_url = f"{_oidc_base()}/userinfo"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            info_resp = await client.post(userinfo_url, data={"access_token": sso_access_token})
    except Exception as e:
        logger.error("SSO userinfo 请求失败: %s", e)
        raise HTTPException(status_code=502, detail=f"SSO 用户信息获取失败: {e}")

    if info_resp.status_code != 200:
        logger.error("SSO userinfo 响应异常: %s %s", info_resp.status_code, info_resp.text)
        raise HTTPException(status_code=401, detail="SSO access_token 无效")

    userinfo = info_resp.json()
    employee_id = userinfo.get("user_id") or userinfo.get("xinmeiti_user_id") or ""
    if not employee_id:
        logger.error("SSO userinfo 无工号: %s", userinfo)
        raise HTTPException(status_code=400, detail="SSO 未返回用户工号")

    family_name = userinfo.get("family_name", "")
    given_name = userinfo.get("given_name", "")
    real_name = f"{family_name}{given_name}".strip() or userinfo.get("name", "")
    phone = userinfo.get("phone", "")

    logger.info("SSO 登录：工号=%s, 姓名=%s", employee_id, real_name)

    # ---- Step 3: 匹配本系统用户 ----
    # 优先按 sso_user_id 查找
    user = get_user_by_sso_id(db, employee_id)

    # 若未绑定 SSO，尝试按 username（工号）匹配并自动绑定
    if not user:
        user = get_user_by_username(db, employee_id)
        if user:
            bind_user_sso(db, user.id, employee_id)
            logger.info("SSO 自动绑定已有用户: username=%s -> sso_user_id=%s", user.username, employee_id)

    # 若仍无匹配，自动创建待审批用户
    if not user:
        random_pw = get_password_hash(f"sso_{employee_id}_{settings.SECRET_KEY[:8]}")
        user = create_sso_user(
            db,
            sso_user_id=employee_id,
            real_name=real_name or None,
            password_hash=random_pw,
            username=employee_id,
        )
        logger.info("SSO 自动创建用户: username=%s, real_name=%s, status=pending", employee_id, real_name)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="首次登录已自动注册，请等待管理员审批后再登录",
        )

    # 检查用户状态
    user_status = getattr(user, "status", "approved") or "approved"
    if user_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的账号待管理员审核，审核通过后方可登录",
        )

    # 更新真实姓名（若 SSO 提供了且本地为空）
    if real_name and not user.real_name:
        user.real_name = real_name
        db.commit()
        db.refresh(user)

    # ---- Step 4: 签发本系统 JWT ----
    version = getattr(user, "token_version", 0) or 0
    token = create_access_token(subject=user.id, token_version=version)
    material_scopes = _user_material_scopes(user)

    return LoginResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            real_name=getattr(user, "real_name", None),
            role=user.role,
            material_scopes=material_scopes,
        ),
    )


@router.post("/auth/sso-logout")
async def sso_logout():
    """
    SSO 单点登出（可选）。
    前端调用本接口后，后端向 Keycloak 发送登出请求。
    注意：单点登出会使同一浏览器下其他已集成 SSO 的应用也登出。
    """
    # 前端主要调用本系统的 logout 清除本地 token 即可
    # 若需要真正的 SSO 单点登出，需要传入 refresh_token
    return {"message": "已登出本系统。如需完全登出 SSO，请关闭浏览器或访问 SSO 登出页面。"}
