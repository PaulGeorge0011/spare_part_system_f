# app/api/v1/wechat.py
import logging
import secrets
import time
from urllib.parse import quote_plus

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token
from app.crud.user import get_user_by_wechat_userid, create_pending_wechat_user, bind_user_wechat
from app.api.v1.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# 绑定企业微信临时 token：token -> (user_id, expiry_ts)，5 分钟有效
_bind_token_store: dict[str, tuple[int, float]] = {}
BIND_TOKEN_TTL = 300


def _store_bind_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _bind_token_store[token] = (user_id, time.time() + BIND_TOKEN_TTL)
    return token


def _get_bind_user_id(token: str) -> int | None:
    if token not in _bind_token_store:
        return None
    user_id, expiry = _bind_token_store[token]
    if time.time() > expiry:
        _bind_token_store.pop(token, None)
        return None
    return user_id


def _clear_bind_token(token: str) -> None:
    _bind_token_store.pop(token, None)


def _wechat_configured() -> bool:
    return bool(
        settings.WECHAT_CORP_ID
        and settings.WECHAT_CORP_SECRET
        and settings.WECHAT_AGENT_ID
        and settings.WECHAT_REDIRECT_URI
    )


def _build_wechat_auth_url(state: str) -> str:
    redirect_uri = quote_plus(settings.WECHAT_REDIRECT_URI.strip())
    return (
        "https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={settings.WECHAT_CORP_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=snsapi_base"
        f"&agentid={settings.WECHAT_AGENT_ID}"
        f"&state={quote_plus(state)}"
        "#wechat_redirect"
    )


@router.get("/wechat/auth-url", tags=["企业微信"])
async def get_auth_url():
    """返回企业微信 OAuth2 扫码授权链接（登录/注册）。未配置时 url 为空。"""
    if not _wechat_configured():
        return {"url": "", "message": "未配置企业微信（WECHAT_CORP_ID / SECRET / AGENT_ID / REDIRECT_URI）"}
    return {"url": _build_wechat_auth_url("spare_part")}


@router.get("/wechat/bind-auth-url", tags=["企业微信"])
async def get_bind_auth_url(
    current_user: User = Depends(get_current_user),
):
    """返回企业微信 OAuth2 扫码授权链接（绑定当前账号）。需登录后调用。"""
    if not _wechat_configured():
        return {"url": "", "message": "未配置企业微信"}
    token = _store_bind_token(current_user.id)
    return {"url": _build_wechat_auth_url(f"bind_{token}")}


@router.get("/wechat/callback", tags=["企业微信"])
async def wechat_callback(
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    """
    企业微信授权回调。
    - state=bind_xxx：绑定当前账号与企业微信，重定向到前端 ?wechat_bind=success 或 already_used / expired
    - 其他：登录或创建待审批用户，重定向到前端 ?token=... 或 ?pending=1 或 ?wechat_error=...
    """
    base = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    login_url = f"{base}/login"
    home_url = f"{base}/"

    if not _wechat_configured():
        return RedirectResponse(url=f"{login_url}?wechat_error=not_configured", status_code=302)

    if not code:
        return RedirectResponse(url=f"{login_url}?wechat_error=no_code", status_code=302)

    try:
        r = httpx.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={
                "corpid": settings.WECHAT_CORP_ID,
                "corpsecret": settings.WECHAT_CORP_SECRET,
            },
            timeout=10,
        )
        data = r.json()
        if data.get("errcode") != 0:
            logger.warning("企业微信 gettoken 失败: %s", data)
            return RedirectResponse(url=f"{login_url}?wechat_error=token_fail", status_code=302)
        token = data.get("access_token")

        r2 = httpx.get(
            "https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo",
            params={"access_token": token, "code": code},
            timeout=10,
        )
        ui = r2.json()
        if ui.get("errcode") != 0:
            logger.warning("企业微信 getuserinfo 失败: %s", ui)
            return RedirectResponse(url=f"{login_url}?wechat_error=userinfo_fail", status_code=302)

        userid = ui.get("userid") or ui.get("UserId")
        if not userid:
            return RedirectResponse(url=f"{login_url}?wechat_error=no_userid", status_code=302)

        name = ui.get("name") or userid

        # 绑定流程：state=bind_<token>
        if state and state.startswith("bind_") and len(state) > 5:
            bind_token = state[5:]
            user_id = _get_bind_user_id(bind_token)
            _clear_bind_token(bind_token)
            if not user_id:
                return RedirectResponse(url=f"{home_url}?wechat_bind=expired", status_code=302)
            ok = bind_user_wechat(db, user_id, userid, name)
            if not ok:
                return RedirectResponse(url=f"{home_url}?wechat_bind=already_used", status_code=302)
            return RedirectResponse(url=f"{home_url}?wechat_bind=success", status_code=302)

        # 登录/注册流程
        user = get_user_by_wechat_userid(db, userid)
        if user:
            status_val = getattr(user, "status", "approved") or "approved"
            if status_val == "approved":
                version = getattr(user, "token_version", 0) or 0
                t = create_access_token(subject=user.id, token_version=version)
                return RedirectResponse(url=f"{login_url}?token={t}", status_code=302)
            return RedirectResponse(url=f"{login_url}?pending=1", status_code=302)

        pw = secrets.token_urlsafe(32)
        create_pending_wechat_user(
            db,
            wechat_userid=userid,
            wechat_name=name,
            password_hash=get_password_hash(pw),
        )
        return RedirectResponse(url=f"{login_url}?pending=1", status_code=302)

    except Exception as e:
        logger.exception("企业微信 callback 异常: %s", e)
        return RedirectResponse(url=f"{login_url}?wechat_error=exception", status_code=302)
