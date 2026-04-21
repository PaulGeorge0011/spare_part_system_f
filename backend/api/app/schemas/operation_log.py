from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from ..core.datetime_utils import ensure_utc_aware


class OperationLogListResponse(BaseModel):
    """操作日志列表分页返回：data + total"""
    data: List["OperationLogResponse"] = Field(..., description="当前页记录")
    total: int = Field(..., description="符合条件的总条数")


class OperationLogResponse(BaseModel):
  """操作日志返回模型"""

  id: int
  created_at: datetime = Field(..., description="操作时间")

  user_id: Optional[int] = Field(None, description="操作人用户ID")
  username: Optional[str] = Field(None, description="操作人用户名")
  real_name: Optional[str] = Field(None, description="操作人真实姓名")

  module: str = Field(..., description="业务模块，如 spare_part / requisition / inventory 等")
  action: str = Field(..., description="操作类型，如 create / update / delete / requisition 等")
  entity_type: Optional[str] = Field(None, description="实体类型，如 spare_part / requisition_log 等")
  entity_id: Optional[int] = Field(None, description="实体ID")

  summary: Optional[str] = Field(None, description="操作简要说明")
  detail: Optional[str] = Field(None, description="操作详情（JSON 或文本）")

  @field_validator("created_at", mode="before")
  @classmethod
  def _ensure_utc_aware(cls, v):
    return ensure_utc_aware(v) if v is not None else v

  class Config:
    from_attributes = True


OperationLogListResponse.model_rebuild()

