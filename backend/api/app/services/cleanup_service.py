# app/services/cleanup_service.py
from sqlalchemy.orm import Session
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..core.database import get_db
from ..core.datetime_utils import utc_now
from ..utils.minio_client import minio_client
from ..crud.image import cleanup_temp_images

def cleanup_expired_temp_images():
    """清理过期的临时图片"""
    try:
        print(f"[{utc_now()}] 开始清理过期临时图片...")
        
        # 清理数据库中的临时图片记录
        db = next(get_db())
        deleted_count = cleanup_temp_images(db, hours_old=24)
        
        # 清理Redis中的临时图片记录（需要实现）
        # minio_client.redis_client.cleanup_expired_temp_images()
        
        print(f"[{utc_now()}] 清理完成，删除了 {deleted_count} 条记录")
        
    except Exception as e:
        print(f"[{utc_now()}] 清理临时图片失败: {e}")

def start_cleanup_scheduler():
    """启动定时清理任务"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        cleanup_expired_temp_images,
        trigger=IntervalTrigger(hours=1),  # 每小时执行一次
        id='cleanup_temp_images',
        name='清理过期临时图片',
        replace_existing=True
    )
    scheduler.start()
    print("临时图片清理任务已启动")