# app/models/requisition_log.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class RequisitionLog(Base):
    """备件领用记录"""

    __tablename__ = "requisition_logs"

    id = Column(Integer, primary_key=True, index=True)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, comment="领用数量")
    physical_stock_before = Column(Integer, nullable=False, comment="领用前修复件库存")
    physical_stock_after = Column(Integer, nullable=False, comment="领用后修复件库存")
    remark = Column(Text, comment="备注")
    requisition_at = Column(DateTime(timezone=True), server_default=func.now(), comment="领用时间")
    requisitioner_name = Column(String(100), nullable=False, comment="领用人")
    operator_name = Column(String(100), nullable=True, comment="操作人（系统登录用户）")
    requisition_reason = Column(String(500), nullable=True, comment="领用原因")
    usage_location = Column(String(200), nullable=True, comment="使用地点")

    def __repr__(self):
        return f"<RequisitionLog(id={self.id}, spare_part_id={self.spare_part_id}, quantity={self.quantity})>"
