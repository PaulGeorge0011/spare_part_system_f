# app/schemas/image.py
from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional, List
from datetime import datetime

from ..core.datetime_utils import ensure_utc_aware, utc_now

class ImageBase(BaseModel):
    material_code: str
    filename: str

class ImageCreate(BaseModel):
    material_code: str
    filename: str
    object_name: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    upload_id: Optional[str] = None
    is_temp: int = 0
    spare_part_id: Optional[int] = None

class ImageUpdate(BaseModel):
    spare_part_id: Optional[int] = None
    is_temp: Optional[int] = None
    confirmed_at: Optional[datetime] = None

class ImageResponse(ImageBase):
    id: int
    object_name: str
    url: str
    size: Optional[int] = None
    content_type: Optional[str] = None
    is_temp: int
    upload_id: Optional[str] = None
    spare_part_id: Optional[int] = None
    uploaded_at: datetime
    confirmed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TempImageUploadResponse(BaseModel):
    """临时图片上传响应"""
    success: bool = True
    message: str = "临时图片上传成功"
    upload_id: str
    temp_url: str
    filename: str
    material_code: str
    size: int
    uploaded_at: datetime = Field(default_factory=utc_now)

class ImageConfirmResponse(BaseModel):
    """图片确认响应"""
    success: bool = True
    message: str = "图片确认成功"
    upload_id: str
    object_name: str
    permanent_url: str
    filename: str
    material_code: str
    spare_part_id: Optional[int] = None
    confirmed_at: datetime = Field(default_factory=utc_now)
    image_index: Optional[int] = None  # 新增字段

class ImageInfo(BaseModel):
    """图片信息"""
    path: str
    url: str
    size: int
    filename: str
    
    class Config:
        from_attributes = True

class ImageDeleteResponse(BaseModel):
    """图片删除响应"""
    success: bool
    message: str
    deleted_ids: List[int] = []
    deleted_objects: List[str] = []
    
    class Config:
        from_attributes = True

class BulkImageConfirmRequest(BaseModel):
    """批量确认图片请求"""
    upload_ids: List[str]
    spare_part_id: Optional[int] = None