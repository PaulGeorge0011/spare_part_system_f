# app/crud/user.py
import json
import secrets
from sqlalchemy.orm import Session
from typing import List

from ..models.user import User


def create_user(
    db: Session,
    username: str,
    password_hash: str,
    role: str = "requisition_clerk",
    status: str = "approved",
    real_name: str | None = None,
) -> User:
    """创建用户。status=approved 可正常使用，status=pending 需管理员审批后才有权限。"""
    u = User(
        username=username.strip(),
        password_hash=password_hash,
        role=role,
        status=status,
        real_name=(real_name or "").strip() or None,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session) -> List[User]:
    """获取所有用户（管理员用）"""
    return db.query(User).order_by(User.id).all()


def get_user_by_wechat_userid(db: Session, wechat_userid: str) -> User | None:
    """按企业微信 userid 查找用户"""
    if not wechat_userid:
        return None
    return db.query(User).filter(User.wechat_userid == wechat_userid).first()


def update_user_permissions(db: Session, user_id: int, permissions: dict) -> User | None:
    """更新用户新模块权限。传入空字典则清空所有新模块权限。不影响 token_version（权限变更在下次请求时生效）。"""
    u = get_user_by_id(db, user_id)
    if not u:
        return None
    u.permissions = json.dumps(permissions, ensure_ascii=False) if permissions else None
    db.commit()
    db.refresh(u)
    return u


def update_user_role(db: Session, user_id: int, role: str) -> User | None:
    """更新用户角色。合法 role: admin | requisition_clerk。会递增 token_version 使该用户旧 token 失效。"""
    u = get_user_by_id(db, user_id)
    if not u:
        return None
    u.role = role
    u.token_version = (getattr(u, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(u)
    return u


def update_user_password(db: Session, user_id: int, new_password_hash: str) -> User | None:
    """更新用户密码。会递增 token_version 使该用户旧 token 失效，需重新登录。"""
    u = get_user_by_id(db, user_id)
    if not u:
        return None
    u.password_hash = new_password_hash
    u.token_version = (getattr(u, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(u)
    return u


def approve_user(db: Session, user_id: int, role: str) -> User | None:
    """审批通过：将 status 设为 approved 并设置 role。会递增 token_version 使该用户旧 token 失效。"""
    u = get_user_by_id(db, user_id)
    if not u or getattr(u, "status", "approved") != "pending":
        return None
    u.status = "approved"
    u.role = role
    u.token_version = (getattr(u, "token_version", 0) or 0) + 1
    db.commit()
    db.refresh(u)
    return u


def reject_user(db: Session, user_id: int) -> bool:
    """审批拒绝：删除待审批用户。"""
    u = get_user_by_id(db, user_id)
    if not u or getattr(u, "status", "approved") != "pending":
        return False
    db.delete(u)
    db.commit()
    return True


def delete_user(db: Session, user_id: int) -> bool:
    """删除用户。不能删除用户名为 admin 的超级管理员，返回 False。"""
    u = get_user_by_id(db, user_id)
    if not u or (u.username == "admin"):
        return False
    db.delete(u)
    db.commit()
    return True


def bind_user_wechat(
    db: Session,
    user_id: int,
    wechat_userid: str,
    wechat_name: str | None = None,
) -> bool:
    """将当前用户与企业微信绑定。若该企业微信已绑定其他用户则返回 False。"""
    existing = get_user_by_wechat_userid(db, wechat_userid)
    if existing and existing.id != user_id:
        return False
    u = get_user_by_id(db, user_id)
    if not u:
        return False
    u.wechat_userid = wechat_userid
    u.wechat_name = wechat_name or None
    db.commit()
    return True


def get_user_by_sso_id(db: Session, sso_user_id: str) -> User | None:
    """按 SSO 工号（Keycloak user_id）查找用户"""
    if not sso_user_id:
        return None
    return db.query(User).filter(User.sso_user_id == sso_user_id).first()


def create_sso_user(
    db: Session,
    sso_user_id: str,
    real_name: str | None,
    password_hash: str,
    username: str | None = None,
) -> User:
    """创建 SSO 登录的用户。username 默认使用工号，status=pending 需管理员审批。"""
    uname = (username or sso_user_id).strip()
    u = User(
        username=uname,
        password_hash=password_hash,
        role="requisition_clerk",
        status="pending",
        sso_user_id=sso_user_id,
        real_name=(real_name or "").strip() or None,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def bind_user_sso(db: Session, user_id: int, sso_user_id: str) -> bool:
    """将现有用户与 SSO 工号绑定。若该工号已绑定其他用户则返回 False。"""
    existing = get_user_by_sso_id(db, sso_user_id)
    if existing and existing.id != user_id:
        return False
    u = get_user_by_id(db, user_id)
    if not u:
        return False
    u.sso_user_id = sso_user_id
    db.commit()
    return True


def create_pending_wechat_user(
    db: Session,
    wechat_userid: str,
    wechat_name: str | None,
    password_hash: str,
) -> User:
    """创建待审批的企业微信用户。username 使用 wx_{userid}，避免与现有用户冲突。"""
    username = f"wx_{wechat_userid}"
    u = User(
        username=username,
        password_hash=password_hash,
        role="requisition_clerk",
        status="pending",
        wechat_userid=wechat_userid,
        wechat_name=wechat_name or None,
        real_name=wechat_name or None,  # 企业微信用户以 wechat_name 作为真实姓名
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
