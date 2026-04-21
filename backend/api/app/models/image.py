# app/models/image.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base
from ..core.datetime_utils import utc_now

class SparePartImage(Base):
    __tablename__ = "spare_part_images"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 基础信息
    material_code = Column(String(100), nullable=False, index=True, comment="物料编码")
    object_name = Column(String(500), nullable=False, comment="MINIO对象名称")
    filename = Column(String(255), nullable=False, comment="文件名")
    original_filename = Column(String(255), comment="原始文件名")
    content_type = Column(String(100), comment="文件类型")
    size = Column(Integer, comment="文件大小(字节)")
    
    # 状态信息
    is_temp = Column(Boolean, default=True, comment="是否为临时图片")
    upload_id = Column(String(36), unique=True, nullable=True, index=True, comment="上传ID")
    
    # 时间信息
    uploaded_at = Column(DateTime, default=utc_now, comment="上传时间")
    confirmed_at = Column(DateTime, nullable=True, comment="确认时间")
    
    # 外键关系
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="SET NULL"), nullable=True, comment="关联备件ID")
    
    # 定义与备件的关系
    spare_part = relationship("SparePart", back_populates="images")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.upload_id:
            self.upload_id = str(uuid.uuid4())
    
    def __repr__(self):
        return f"<SparePartImage(id={self.id}, filename='{self.filename}', material_code='{self.material_code}')>"