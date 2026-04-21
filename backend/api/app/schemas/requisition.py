# app/schemas/requisition.py
from typing import Optional
from pydantic import BaseModel, Field


class RequisitionRequest(BaseModel):
    """领用请求。领用人由当前登录用户的真实姓名自动确定，请求体中无需传递。"""
    quantity: int = Field(..., ge=1, description="领用数量")
    requisition_reason: str = Field(..., min_length=1, max_length=500, description="领用原因（必填）")
    usage_location: str = Field(..., min_length=1, max_length=200, description="使用地点（必填）")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class RequisitionResponse(BaseModel):
    """领用响应"""
    success: bool = True
    message: str = "领用成功"
    spare_part_id: int = 0
    quantity: int = 0
    physical_stock_before: int = 0
    physical_stock_after: int = 0


class ReturnRequest(BaseModel):
    """归还请求。归还人由当前登录用户自动确定。"""
    quantity: int = Field(..., ge=1, description="归还数量")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class ReturnResponse(BaseModel):
    """归还响应"""
    success: bool = True
    message: str = "归还成功"
    spare_part_id: int = 0
    quantity: int = 0
    physical_stock_before: int = 0
    physical_stock_after: int = 0
