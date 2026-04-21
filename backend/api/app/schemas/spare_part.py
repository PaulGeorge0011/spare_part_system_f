from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional, Any, List
from pydantic.functional_validators import field_validator
from ..core.datetime_utils import ensure_utc_aware

class SparePartBase(BaseModel):
    """备件共享基础字段。唯一性：货位号+规格型号联合区分，MES 编码可空。"""
    location_code: str = Field(..., min_length=1, max_length=50, description='货位号，如：A-01-02')
    mes_material_code: Optional[str] = Field(default='', max_length=100, description='MES系统物料编码，允许为空')
    mes_material_desc: Optional[str] = Field(None, max_length=255, description='MES物料描述')
    physical_material_desc: Optional[str] = Field(None, description='实物物料描述')
    specification_model: Optional[str] = Field(None, max_length=255, description='规格型号，与货位号联合用于查重')
    applicable_model: Optional[str] = Field(None, max_length=255, description='适用机型，多个用逗号隔开')
    brand: Optional[str] = Field(None, max_length=100, description='品牌')
    mes_stock: Optional[float] = Field(0.0, ge=0, description='MES库存数量')
    physical_stock: Optional[float] = Field(0.0, ge=0, description='实物库存数量')
    unit: Optional[str] = Field('个', max_length=20, description='数量单位')
    remarks: Optional[str] = Field(None, description='备注信息')
    storage_location: Optional[str] = Field(None, max_length=255, description='具体存放地')
    # 注意：图片URL在创建时通常不是必须的，可能是后续上传后更新
    physical_image_url: Optional[str] = Field(None, max_length=500, description='实物图片URL')
    physical_image_url2: Optional[str] = Field(None, max_length=500, description='实物图片2 URL')

    @field_validator('mes_material_code')
    @classmethod
    def validate_mes_code_format(cls, v: Optional[str]) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return ''
        return str(v).strip().upper()

    model_config = ConfigDict(from_attributes=True)

class SparePartCreate(SparePartBase):
    """用于创建备件的模式，继承所有基础字段"""
    # 可以在此处添加创建时特有的验证逻辑
    image_upload_ids: Optional[List[str]] = Field(
        None,
        description="临时图片upload_id列表（创建时用于关联图片）"
    )

class SparePartUpdate(BaseModel):
    """用于更新备件的模式，所有字段可选"""
    location_code: Optional[str] = Field(None, min_length=1, max_length=50)
    mes_material_code: Optional[str] = Field(None, min_length=1, max_length=100)
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
    image_upload_ids: Optional[List[str]] = Field(
        None,
        description="新增的临时图片upload_id列表（用于确认并关联到该备件）"
    )
    image_ids_to_delete: Optional[List[int]] = Field(
        None,
        description="需要删除的图片记录ID列表（SparePartImage.id）"
    )



    model_config = ConfigDict(from_attributes=True)

class SparePart(SparePartBase):
    """用于API响应的完整备件模式，包含系统生成的字段"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # 继承SparePartBase的所有字段

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _ensure_utc_aware(cls, v):
        return ensure_utc_aware(v) if v is not None else v