# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from ..core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    real_name = Column(String(100), nullable=True, comment="真实姓名（领用时作为领用人）")
    password_hash = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="requisition_clerk")  # admin | requisition_clerk
    material_scopes = Column(String(200), nullable=True, default="electrical,mechanical", comment="物资范围：electrical,mechanical 等，逗号分隔，空则视为全部")
    status = Column(String(32), nullable=False, default="approved", index=True)  # approved | pending
    wechat_userid = Column(String(64), nullable=True, unique=True, index=True)
    wechat_name = Column(String(100), nullable=True)
    sso_user_id = Column(String(64), nullable=True, unique=True, index=True, comment="SSO 工号（Keycloak user_id）")
    token_version = Column(Integer, nullable=False, default=0, comment="权限变更时递增，使旧 token 失效")
    permissions = Column(String(2000), nullable=True, comment="模块权限JSON，格式：{\"module_id\": \"admin|editor|viewer\"}，仅用于非旧版模块")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
