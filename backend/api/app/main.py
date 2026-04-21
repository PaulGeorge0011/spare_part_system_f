from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
# 注意：这里使用相对导入，因为我们在 app 模块内
from .core.config import settings
from .core.database import engine, Base
from .models import spare_part, image, requisition_log, requisition_return_log, user, inbound_log, outbound_log  # 关键！必须导入模型
from .models import mechanical_spare_part, mechanical_spare_part_image, mechanical_requisition_log, mechanical_requisition_return_log, mechanical_inbound_log, mechanical_outbound_log
from .services.cleanup_service import start_cleanup_scheduler

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("应用启动中...")
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        logger.warning("⚠️ SECRET_KEY 仍为默认值，生产环境请在环境变量中设置强随机 SECRET_KEY")
    if settings.DEBUG:
        logger.warning("⚠️ DEBUG=True，生产环境建议设置 DEBUG=False")
    start_cleanup_scheduler()
    
    # 检查表是否存在，如果存在则跳过创建
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    if inspector.has_table("spare_parts"):
        logger.info("✅ 检测到 spare_parts 表已存在，跳过创建")
        try:
            from migrate_spare_part_unique import run as run_migrate_spare_part_unique
            run_migrate_spare_part_unique()
            logger.info("✅ spare_parts 唯一约束迁移已执行（若已迁移则跳过）")
        except Exception as e:
            logger.warning("spare_parts 唯一约束迁移跳过或失败（可手动执行 migrate_spare_part_unique.py）: %s", e)
        try:
            from migrate_spare_part_loc_spec import run as run_migrate_loc_spec
            run_migrate_loc_spec()
            logger.info("✅ spare_parts 货位+规格唯一约束迁移已执行（若已迁移则跳过）")
        except Exception as e:
            logger.warning("spare_parts 货位+规格迁移跳过或失败（可手动执行 migrate_spare_part_loc_spec.py）: %s", e)
    else:
        logger.info("开始创建数据库表...")
        try:
            # 这里是关键：调用create_all
            Base.metadata.create_all(bind=engine)
            logger.info("✅ 数据库表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建数据库表时出错: {e}")
            raise
    if inspector.has_table("spare_part_images"):
        logger.info("✅ 检测到 spare_part_images 表已存在，跳过创建")
    else:
        logger.info("开始创建数据库表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ 数据库表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建数据库表时出错: {e}")
            raise
    if not inspector.has_table("requisition_return_logs"):
        logger.info("创建 requisition_return_logs 表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ requisition_return_logs 表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建 requisition_return_logs 表时出错: {e}")
    else:
        logger.info("✅ 检测到 requisition_return_logs 表已存在，跳过创建")

    if not inspector.has_table("mechanical_requisition_return_logs"):
        logger.info("创建 mechanical_requisition_return_logs 表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ mechanical_requisition_return_logs 表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建 mechanical_requisition_return_logs 表时出错: {e}")
    else:
        logger.info("✅ 检测到 mechanical_requisition_return_logs 表已存在，跳过创建")

    if inspector.has_table("requisition_logs"):
        logger.info("✅ 检测到 requisition_logs 表已存在，跳过创建")
        # 若表已存在，检查并添加 operator_name 列（兼容旧库）
        try:
            from sqlalchemy import text
            cols = [c["name"] for c in inspector.get_columns("requisition_logs")]
            with engine.connect() as conn:
                if "operator_name" not in cols:
                    conn.execute(text("ALTER TABLE requisition_logs ADD COLUMN operator_name VARCHAR(100)"))
                    conn.commit()
                    logger.info("✅ requisition_logs 表已添加 operator_name 列")
                if "requisitioner_name" not in cols:
                    conn.execute(text("ALTER TABLE requisition_logs ADD COLUMN requisitioner_name VARCHAR(100) NOT NULL DEFAULT '—'"))
                    conn.commit()
                    logger.info("✅ requisition_logs 表已添加 requisitioner_name 列")
                if "requisition_reason" not in cols:
                    conn.execute(text("ALTER TABLE requisition_logs ADD COLUMN requisition_reason VARCHAR(500) NULL COMMENT '领用原因'"))
                    conn.commit()
                    logger.info("✅ requisition_logs 表已添加 requisition_reason 列")
                if "usage_location" not in cols:
                    conn.execute(text("ALTER TABLE requisition_logs ADD COLUMN usage_location VARCHAR(200) NULL COMMENT '使用地点'"))
                    conn.commit()
                    logger.info("✅ requisition_logs 表已添加 usage_location 列")
        except Exception as e:
            logger.warning("requisition_logs 列检查/添加跳过: %s", e)
    else:
        logger.info("创建 requisition_logs 表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ requisition_logs 表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建 requisition_logs 表时出错: {e}")
            raise

    # 确保 inbound_logs 表存在（编辑表单增加实物库存时记录入库）
    if inspector.has_table("inbound_logs"):
        logger.info("✅ 检测到 inbound_logs 表已存在，跳过创建")
    else:
        logger.info("创建 inbound_logs 表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ inbound_logs 表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建 inbound_logs 表时出错: {e}")
            raise

    # 确保 outbound_logs 表存在（编辑表单减少实物库存时记录管理出库）
    if inspector.has_table("outbound_logs"):
        logger.info("✅ 检测到 outbound_logs 表已存在，跳过创建")
    else:
        logger.info("创建 outbound_logs 表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ outbound_logs 表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建 outbound_logs 表时出错: {e}")
            raise

    # 确保 mechanical_requisition_logs 新列存在
    if inspector.has_table("mechanical_requisition_logs"):
        try:
            from sqlalchemy import text
            cols = [c["name"] for c in inspector.get_columns("mechanical_requisition_logs")]
            with engine.connect() as conn:
                if "requisition_reason" not in cols:
                    conn.execute(text("ALTER TABLE mechanical_requisition_logs ADD COLUMN requisition_reason VARCHAR(500) NULL COMMENT '领用原因'"))
                    conn.commit()
                    logger.info("✅ mechanical_requisition_logs 表已添加 requisition_reason 列")
                if "usage_location" not in cols:
                    conn.execute(text("ALTER TABLE mechanical_requisition_logs ADD COLUMN usage_location VARCHAR(200) NULL COMMENT '使用地点'"))
                    conn.commit()
                    logger.info("✅ mechanical_requisition_logs 表已添加 usage_location 列")
        except Exception as e:
            logger.warning("mechanical_requisition_logs 列检查/添加跳过: %s", e)

    # 确保机械备件相关表存在
    if inspector.has_table("mechanical_spare_parts"):
        logger.info("✅ 检测到 mechanical_spare_parts 表已存在，跳过创建")
    else:
        logger.info("创建机械备件相关表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ 机械备件相关表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建机械备件表时出错: {e}")
            raise

    # 确保 operation_logs 日志表存在（用于记录操作记录）
    if inspector.has_table("operation_logs"):
        logger.info("✅ 检测到 operation_logs 表已存在，跳过创建")
        try:
            from sqlalchemy import text
            cols = [c["name"] for c in inspector.get_columns("operation_logs")]
            if "real_name" not in cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE operation_logs ADD COLUMN real_name VARCHAR(100) NULL"))
                    conn.commit()
                    logger.info("✅ operation_logs 表已添加 real_name 列")
        except Exception as e:
            logger.warning("operation_logs 表 real_name 列检查/添加跳过: %s", e)
    else:
        logger.info("创建 operation_logs 表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ operation_logs 表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建 operation_logs 表时出错: {e}")
            raise
    if not inspector.has_table("users"):
        logger.info("创建 users 表...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ users 表创建完成！")
        except Exception as e:
            logger.error(f"❌ 创建 users 表时出错: {e}")
            raise
    else:
        try:
            from sqlalchemy import text
            cols = [c["name"] for c in inspector.get_columns("users")]
            with engine.connect() as conn:
                if "status" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'approved'"))
                    conn.commit()
                    logger.info("✅ users 表已添加 status 列")
                if "wechat_userid" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN wechat_userid VARCHAR(64) NULL"))
                    conn.commit()
                    logger.info("✅ users 表已添加 wechat_userid 列")
                if "wechat_name" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN wechat_name VARCHAR(100) NULL"))
                    conn.commit()
                    logger.info("✅ users 表已添加 wechat_name 列")
                if "token_version" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"))
                    conn.commit()
                    logger.info("✅ users 表已添加 token_version 列")
                if "real_name" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN real_name VARCHAR(100) NULL"))
                    conn.commit()
                    logger.info("✅ users 表已添加 real_name 列")
                if "material_scopes" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN material_scopes VARCHAR(200) NULL DEFAULT 'electrical,mechanical'"))
                    conn.commit()
                    logger.info("✅ users 表已添加 material_scopes 列")
                if "sso_user_id" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN sso_user_id VARCHAR(64) NULL"))
                    conn.commit()
                    logger.info("✅ users 表已添加 sso_user_id 列")
                if "permissions" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN permissions VARCHAR(2000) NULL COMMENT '模块权限JSON'"))
                    conn.commit()
                    logger.info("✅ users 表已添加 permissions 列")
        except Exception as e:
            logger.warning("users 表列检查/添加跳过: %s", e)
    # 初始化默认用户（管理员 admin / admin123，备件领用员 clerk / clerk123）
    from .core.database import SessionLocal
    from .core.security import get_password_hash, verify_password
    from .models.user import User
    from .crud.user import get_user_by_username
    db = SessionLocal()
    try:
        for username, password, role in [
            ("admin", "admin123", "admin"),
            ("clerk", "clerk123", "requisition_clerk"),
        ]:
            existing_user = get_user_by_username(db, username)
            if not existing_user:
                # 创建新用户
                u = User(username=username, password_hash=get_password_hash(password), role=role)
                db.add(u)
                logger.info(f"✅ 创建默认用户: {username} ({role})")
            else:
                # 用户已存在，检查并更新密码（确保密码正确）
                if not verify_password(password, existing_user.password_hash):
                    existing_user.password_hash = get_password_hash(password)
                    logger.info(f"✅ 更新用户密码: {username} ({role})")
                if existing_user.role != role:
                    existing_user.role = role
                    logger.info(f"✅ 更新用户角色: {username} -> {role}")
                else:
                    logger.info(f"✅ 用户已存在: {username} ({role})")
        db.commit()
    except Exception as e:
        logger.error(f"❌ 初始化默认用户时出错: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
    yield  # 应用运行在此处
    # 关闭时
    logger.info("应用关闭中...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if getattr(settings, "DOCS_ENABLED", True) else None,
    docs_url="/api/docs" if getattr(settings, "DOCS_ENABLED", True) else None,
    redoc_url="/api/redoc" if getattr(settings, "DOCS_ENABLED", True) else None,
    lifespan=lifespan,
)

# 配置CORS：优先使用环境变量 CORS_ORIGINS（逗号分隔），空则使用默认开发来源
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://frontend-dev:5173",
    "http://frontend:80",
]
_cors_origins = [o.strip() for o in (settings.CORS_ORIGINS or "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else _default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 直接导入并注册路由（不要在startup事件中延迟导入）
# 首先尝试导入备件管理路由
try:
    from .api.v1 import spare_parts
    app.include_router(spare_parts.router, prefix=settings.API_V1_STR, tags=["备件管理"])
    logger.info("✅ 备件管理路由注册成功")
except ImportError as e:
    logger.error(f"❌ 导入备件管理路由失败: {e}")

try:
    from .api.v1 import mechanical_spare_parts
    app.include_router(mechanical_spare_parts.router, prefix=settings.API_V1_STR, tags=["机械备件管理"])
    logger.info("✅ 机械备件管理路由注册成功")
except ImportError as e:
    logger.error(f"❌ 导入机械备件管理路由失败: {e}")

try:
    from .api.v1 import images
    app.include_router(images.router, prefix=settings.API_V1_STR, tags=["图片管理"])
    logger.info("✅ 图片管理路由注册成功")
except ImportError as e:
    logger.error(f"❌ 导入图片管理路由失败: {e}")

try:
    from .api.v1 import auth
    app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["认证"])
    logger.info("✅ 认证路由注册成功")
except ImportError as e:
    logger.warning("⚠️ 认证路由未实现，跳过注册: %s", e)

try:
    from .api.v1 import inventory
    app.include_router(inventory.router, prefix=settings.API_V1_STR, tags=["库存管理"])
    logger.info("✅ 库存管理路由注册成功")
except ImportError:
    logger.warning("⚠️ 库存管理路由未实现，跳过注册")

try:
    from .api.v1 import operation_logs
    app.include_router(operation_logs.router, prefix=settings.API_V1_STR, tags=["操作记录"])
    logger.info("✅ 操作记录路由注册成功")
except ImportError:
    logger.warning("⚠️ 操作记录路由未实现，跳过注册")

try:
    from .api.v1 import users
    app.include_router(users.router, prefix=settings.API_V1_STR, tags=["用户管理"])
    logger.info("✅ 用户管理路由注册成功")
except ImportError as e:
    logger.warning("⚠️ 用户管理路由未实现，跳过注册: %s", e)

try:
    from .api.v1 import wechat
    app.include_router(wechat.router, prefix=settings.API_V1_STR, tags=["企业微信"])
    logger.info("✅ 企业微信路由注册成功")
except ImportError:
    logger.warning("⚠️ 企业微信路由未实现，跳过注册")

# SSO 单点登录路由（始终注册，接口内部判断 SSO_ENABLED）
try:
    from .api.v1 import sso
    app.include_router(sso.router, prefix=settings.API_V1_STR, tags=["SSO单点登录"])
    if settings.SSO_ENABLED:
        logger.info("✅ SSO 单点登录路由注册成功（已启用）")
    else:
        logger.info("✅ SSO 单点登录路由注册成功（未启用，需配置 SSO_ENABLED=true）")
except ImportError as e:
    logger.warning("⚠️ SSO 路由未实现，跳过注册: %s", e)

try:
    from .api.v1 import ws
    app.include_router(ws.router, prefix=settings.API_V1_STR, tags=["WebSocket"])
    logger.info("✅ WebSocket 实时推送路由注册成功")
except ImportError as e:
    logger.warning("⚠️ WebSocket 路由未实现，跳过注册: %s", e)

try:
    from .api.v1 import reports
    app.include_router(reports.router, prefix=settings.API_V1_STR, tags=["报表统计"])
    logger.info("✅ 报表统计路由注册成功")
except ImportError as e:
    logger.warning("⚠️ 报表统计路由未实现，跳过注册: %s", e)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """未捕获异常时返回 500 并在 body 中带上 request_id，便于与前端请求ID对应查日志"""
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        raise exc
    request_id = (request.headers.get("X-Request-Id") or "").strip()
    logger.exception("未捕获异常 request_id=%s: %s", request_id or "-", exc)
    detail = str(exc) if getattr(settings, "DEBUG", False) else "服务器内部错误"
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": request_id},
    )


@app.get("/")
async def root():
    return {
        "message": "欢迎使用备件管理系统API",
        "version": settings.VERSION,
        "docs": "/api/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}