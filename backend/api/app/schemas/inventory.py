# app/schemas/inventory.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from ..core.datetime_utils import ensure_utc_aware


class InventoryRecordResponse(BaseModel):
    """库存记录（入库/出库/领用/盘点等）"""

    id: int
    # 事件类型：领用、盘点更新、入库 等
    event_type: str = Field(..., description="出库/入库事件类型：领用、盘点更新等")
    # 入库时间（若有）
    inbound_time: Optional[datetime] = Field(None, description="入库时间")
    # 出库时间（领用时间等）
    outbound_time: Optional[datetime] = Field(None, description="出库时间")
    # 领用人（仅领用事件有值）
    requisitioner_name: Optional[str] = Field(None, description="领用人")
    # 操作人（系统登录用户）
    operator_name: Optional[str] = Field(None, description="操作人")
    # 备件信息
    spare_part_id: int
    location_code: Optional[str] = None
    mes_material_code: Optional[str] = None
    specification_model: Optional[str] = None
    unit: Optional[str] = None
    physical_image_url: Optional[str] = Field(None, description="实物图片1 URL")
    physical_image_url2: Optional[str] = Field(None, description="实物图片2 URL")
    # 数量变化
    quantity: int = Field(..., description="领用/变动数量")
    physical_stock_before: Optional[int] = None
    physical_stock_after: Optional[int] = None
    remark: Optional[str] = None
    requisition_reason: Optional[str] = None
    usage_location: Optional[str] = None
    storage_location: Optional[str] = None

    @field_validator("inbound_time", "outbound_time", mode="before")
    @classmethod
    def _ensure_utc_aware(cls, v):
        return ensure_utc_aware(v) if v is not None else v

    class Config:
        from_attributes = True
