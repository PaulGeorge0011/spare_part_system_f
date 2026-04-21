# app/crud/image.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import timedelta
import logging

from ..core.datetime_utils import utc_now
from ..models.image import SparePartImage
from ..schemas.image import ImageCreate

logger = logging.getLogger(__name__)

def create_image_record(db: Session, image_data: Dict[str, Any]) -> SparePartImage:
    """创建图片记录"""
    db_image = SparePartImage(**image_data)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

def get_image_by_id(db: Session, image_id: int) -> Optional[SparePartImage]:
    """根据ID获取图片"""
    return db.query(SparePartImage).filter(SparePartImage.id == image_id).first()

def get_image_by_upload_id(db: Session, upload_id: str) -> Optional[SparePartImage]:
    """根据上传ID获取图片"""
    return db.query(SparePartImage).filter(SparePartImage.upload_id == upload_id).first()

def get_images_by_spare_part(db: Session, spare_part_id: int) -> List[SparePartImage]:
    """根据备件ID获取所有图片"""
    return db.query(SparePartImage).filter(
        SparePartImage.spare_part_id == spare_part_id
    ).order_by(SparePartImage.uploaded_at.desc()).all()

def get_temp_images_by_material(db: Session, material_code: str) -> List[SparePartImage]:
    """根据物料编码获取所有临时图片"""
    return db.query(SparePartImage).filter(
        SparePartImage.material_code == material_code,
        SparePartImage.is_temp == True,
        SparePartImage.spare_part_id == None
    ).order_by(SparePartImage.uploaded_at.desc()).all()

def confirm_image_record(db: Session, upload_id: str, spare_part_id: Optional[int] = None) -> Optional[SparePartImage]:
    """确认图片记录（将临时图片转为永久）"""
    image = get_image_by_upload_id(db, upload_id)
    if image:
        image.is_temp = False
        image.spare_part_id = spare_part_id
        image.confirmed_at = utc_now().replace(tzinfo=None)
        db.commit()
        db.refresh(image)
    return image

def update_image_record(db: Session, image_id: int, update_data: Dict[str, Any]) -> Optional[SparePartImage]:
    """更新图片记录"""
    image = get_image_by_id(db, image_id)
    if image:
        for key, value in update_data.items():
            setattr(image, key, value)
        db.commit()
        db.refresh(image)
    return image

def delete_image_record(db: Session, image_id: int) -> bool:
    """删除图片记录"""
    image = get_image_by_id(db, image_id)
    if image:
        db.delete(image)
        db.commit()
        return True
    return False

def delete_images_by_spare_part(db: Session, spare_part_id: int) -> int:
    """删除备件的所有图片记录"""
    result = db.query(SparePartImage).filter(
        SparePartImage.spare_part_id == spare_part_id
    ).delete()
    db.commit()
    return result

def cleanup_temp_images(db: Session, hours_old: int = 24) -> int:
    """清理过期的临时图片记录"""
    cutoff_time = utc_now().replace(tzinfo=None) - timedelta(hours=hours_old)
    result = db.query(SparePartImage).filter(
        SparePartImage.is_temp == True,
        SparePartImage.uploaded_at < cutoff_time
    ).delete()
    db.commit()
    return result