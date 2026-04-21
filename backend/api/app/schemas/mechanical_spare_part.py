# app/schemas/mechanical_spare_part.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from pydantic.functional_validators import field_validator
from ..core.datetime_utils import ensure_utc_aware


class MechanicalSparePartBase(BaseModel):
    """机械备件基础字段：与电气一致 + 图号、保管人、来源说明、技术鉴定、处置方式。"""
    location_code: str = Field(..., min_length=1, max_length=50, description="货位号")
    mes_material_code: Optional[str] = Field(default="", max_length=100, description="MES物料编码")
    mes_material_desc: Optional[str] = Field(None, max_length=255)
    physical_material_desc: Optional[str] = Field(None)
    specification_model: Optional[str] = Field(None, max_length=255)
    applicable_model: Optional[str] = Field(None, max_length=255)
    brand: Optional[str] = Field(None, max_length=100)
    mes_stock: Optional[float] = Field(0.0, ge=0)
    physical_stock: Optional[float] = Field(0.0, ge=0)
    unit: Optional[str] = Field("个", max_length=20)
    remarks: Optional[str] = Field(None)
    storage_location: Optional[str] = Field(None, max_length=255)
    physical_image_url: Optional[str] = Field(None, max_length=500)
    physical_image_url2: Optional[str] = Field(None, max_length=500)
    # 机械备件专属
    drawing_no: Optional[str] = Field(None, max_length=100, description="图号")
    custodian: Optional[str] = Field(None, max_length=100, description="保管人")
    source_description: Optional[str] = Field(None, max_length=500, description="来源说明")
    technical_appraisal: Optional[str] = Field(None, max_length=500, description="技术鉴定")
    disposal_method: Optional[str] = Field(None, max_length=200, description="处置方式")

    @field_validator("mes_material_code")
    @classmethod
    def validate_mes_code(cls, v: Optional[str]) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return ""
        return str(v).strip().upper()

    model_config = ConfigDict(from_attributes=True)


class MechanicalSparePartCreate(MechanicalSparePartBase):
    image_upload_ids: Optional[List[str]] = Field(None, description="临时图片 upload_id 列表")


class MechanicalSparePartUpdate(BaseModel):
    location_code: Optional[str] = Field(None, min_length=1, max_length=50)
    mes_material_code: Optional[str] = Field(None, max_length=100)
    mes_material_desc: Optional[str] = Field(None, max_length=255)
    physical_material_desc: Optional[str] = Field(None)
    specification_model: Optional[str] = Field(None, max_length=255)
    applicable_model: Optional[str] = Field(None, max_length=255)
    brand: Optional[str] = Field(None, max_length=100)
    mes_stock: Optional[float] = Field(None, ge=0)
    physical_stock: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    remarks: Optional[str] = Field(None)
    storage_location: Optional[str] = Field(None, max_length=255)
    physical_image_url: Optional[str] = Field(None, max_length=500)
    physical_image_url2: Optional[str] = Field(None, max_length=500)
    drawing_no: Optional[str] = Field(None, max_length=100)
    custodian: Optional[str] = Field(None, max_length=100)
    source_description: Optional[str] = Field(None, max_length=500)
    technical_appraisal: Optional[str] = Field(None, max_length=500)
    disposal_method: Optional[str] = Field(None, max_length=200)
    image_upload_ids: Optional[List[str]] = Field(None, description="新增临时图片 upload_id 列表")
    image_ids_to_delete: Optional[List[int]] = Field(None, description="要删除的图片 ID 列表")

    model_config = ConfigDict(from_attributes=True)


class MechanicalSparePart(MechanicalSparePartBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _ensure_utc_aware(cls, v):
        return ensure_utc_aware(v) if v is not None else v
