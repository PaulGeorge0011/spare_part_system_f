# app/core/config.py
from typing import List, Optional
from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # 项目基础配置
    PROJECT_NAME: str = "备件管理系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://sparepart:sparepart123@mysql:3306/spare_part_db"
    
    # MinIO配置
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "06002336fwbMINIO"
    MINIO_BUCKET_NAME: str = "spareparts"
    MINIO_SECURE: bool = False
    MINIO_REGION: str = "us-east-1"
    
    # 图片上传配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/gif,image/webp,image/bmp"
    ALLOWED_IMAGE_EXTENSIONS: str = ".jpg,.jpeg,.png,.gif,.bmp,.webp"
    IMAGE_UPLOAD_PATH: str = "uploads/images" # 本地文件存储（备选）
    IMAGE_UPLOAD_PREFIX: str = "spare-parts/"
    IMAGE_UPLOAD_PREFIX_MECHANICAL: str = "spare-parts-machine/"  # 机械备件最终目录，与 spare-parts 同级
    
    # 临时图片配置
    TEMP_IMAGE_EXPIRE_HOURS: int = 24  # 临时图片过期时间（小时）
    
    # 其他配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # CORS 允许的来源，逗号分隔；空则使用默认开发来源。生产环境应设置如 https://spare.yourcompany.com
    CORS_ORIGINS: str = ""
    # 是否启用 API 文档（/api/docs、/api/redoc）。生产可设为 False 关闭
    DOCS_ENABLED: bool = True
    
    # Redis配置（用于存储临时图片信息）
    REDIS_URL: str = "redis://redis:6379/0"
    
    # 企业微信（扫码登录/注册，可选）
    WECHAT_CORP_ID: str = ""
    WECHAT_CORP_SECRET: str = ""
    WECHAT_AGENT_ID: str = ""
    WECHAT_REDIRECT_URI: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    
    # SSO 单点登录配置（Keycloak OIDC）
    SSO_ENABLED: bool = False
    SSO_CLIENT_ID: str = ""
    SSO_CLIENT_SECRET: str = ""
    SSO_BASE_URL: str = ""          # Keycloak base URL，如 https://sso.example.com
    SSO_REALM: str = "yxcf"         # Keycloak realm
    SSO_REDIRECT_URI: str = ""      # 授权回调地址，如 https://app.example.com/sso/callback
    
    # Pydantic 2.0+ 配置
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @property
    def allowed_image_types_list(self) -> List[str]:
        """将逗号分隔的字符串转换为列表"""
        if not self.ALLOWED_IMAGE_TYPES:
            return []
        return [item.strip() for item in self.ALLOWED_IMAGE_TYPES.split(",")]
    
    @field_validator("MAX_UPLOAD_SIZE", mode="before")
    @classmethod
    def validate_max_upload_size(cls, v):
        """验证上传大小"""
        if isinstance(v, str):
            if v.endswith("MB"):
                return int(v.replace("MB", "")) * 1024 * 1024
            elif v.endswith("KB"):
                return int(v.replace("KB", "")) * 1024
        return v

settings = Settings()