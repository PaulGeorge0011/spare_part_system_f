# app/models/mechanical_spare_part.py
"""机械备件主表：与电气备件字段一致，另增图号、保管人、来源说明、技术鉴定、处置方式。"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from ..core.database import Base
from sqlalchemy.sql import func


class MechanicalSparePart(Base):
    __tablename__ = "mechanical_spare_parts"
    __table_args__ = (
        UniqueConstraint("location_code", "specification_model", name="uq_mechanical_spare_part_loc_spec"),
        # 性能优化：添加常用查询字段的索引
        Index("ix_mech_spare_part_brand", "brand"),
        Index("ix_mech_spare_part_applicable_model", "applicable_model"),
        Index("ix_mech_spare_part_storage_location", "storage_location"),
        Index("ix_mech_spare_part_updated_at", "updated_at"),
        Index("ix_mech_spare_part_is_active", "is_active"),
        Index("ix_mech_spare_part_custodian", "custodian"),
        # 复合索引：常见筛选组合
        Index("ix_mech_spare_part_brand_model", "brand", "applicable_model"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # 基础信息（与电气一致）
    location_code = Column(String(50), nullable=False, index=True, comment="货位号")
    mes_material_code = Column(String(100), nullable=True, default="", index=True, comment="MES物料编码")
    mes_material_desc = Column(String(200), comment="MES物料描述")
    physical_material_desc = Column(String(200), comment="实物物料描述")
    specification_model = Column(String(200), comment="规格型号")
    applicable_model = Column(String(200), comment="适用机型")
    brand = Column(String(100), comment="品牌")

    # 库存信息
    mes_stock = Column(Integer, default=0, comment="MES库存")
    physical_stock = Column(Integer, default=0, comment="实物库存")
    unit = Column(String(20), default="个", comment="数量单位")

    # 其他信息
    storage_location = Column(String(200), comment="存放地")
    physical_image_url = Column(String(500), comment="实物图片URL")
    physical_image_url2 = Column(String(500), comment="实物图片2URL")
    remarks = Column(Text, comment="备注")

    # 机械备件专属字段
    drawing_no = Column(String(100), comment="图号")
    custodian = Column(String(100), comment="保管人")
    source_description = Column(String(500), comment="来源说明")
    technical_appraisal = Column(String(500), comment="技术鉴定")
    disposal_method = Column(String(200), comment="处置方式")

    # 系统字段
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="最后更新时间")
    is_active = Column(Boolean, default=True, comment="是否有效")

    images = relationship("MechanicalSparePartImage", back_populates="mechanical_spare_part", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MechanicalSparePart(id={self.id}, mes_material_code='{self.mes_material_code}')>"
