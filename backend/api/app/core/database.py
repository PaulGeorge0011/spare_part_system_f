# backend/api/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.core.config import settings  # 导入配置

# 使用配置中的 DATABASE_URL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# 创建数据库引擎
# 注意：echo 使用 DEBUG 配置，生产环境应设为 False 以提高性能
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # 增加连接池大小
    max_overflow=30,  # 增加最大溢出连接
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,  # 连接超时
    echo=settings.DEBUG,  # 根据 DEBUG 配置决定是否显示 SQL
)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类
Base = declarative_base()


def init_db():
    """初始化数据库，创建所有表"""
    try:
        # 导入所有模型以确保它们被注册到Base.metadata
        from ..models import spare_part
        from ..models import image
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        raise
# 依赖注入函数
def get_db():
    """
    获取数据库会话的依赖函数
    在每个请求中创建新会话，请求结束后关闭
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()