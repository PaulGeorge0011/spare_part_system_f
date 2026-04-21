# app/core/security.py
from datetime import timedelta
from typing import Optional

from jose import JWTError, jwt
import bcrypt

from .config import settings
from .datetime_utils import utc_now


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # bcrypt 要求密码是 bytes，且长度不超过72字节
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    token_version: int = 0,
) -> str:
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(subject), "exp": expire, "v": token_version}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Optional[tuple[str, int]]:
    """解码 token，返回 (subject, token_version)。无效或过期返回 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        sub = payload.get("sub")
        if not sub:
            return None
        version = payload.get("v", 0)
        return (sub, version)
    except JWTError:
        return None


# 设置密码链接 token：7 天有效，用于管理员新建用户后发给用户自助设置密码
SETUP_TOKEN_EXPIRE_DAYS = 7


def create_setup_token(user_id: int) -> str:
    """生成设置密码链接用 token（JWT），用于新建用户后发给用户自助设置密码。"""
    expire = utc_now() + timedelta(days=SETUP_TOKEN_EXPIRE_DAYS)
    to_encode = {"purpose": "setup", "uid": user_id, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_setup_token(token: str) -> Optional[int]:
    """解码设置密码 token，返回 user_id。无效或过期返回 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("purpose") != "setup":
            return None
        uid = payload.get("uid")
        if uid is None:
            return None
        return int(uid)
    except (JWTError, ValueError, TypeError):
        return None
