# app/models/requisition_return_log.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class RequisitionReturnLog(Base):
    """电气备件归还记录"""

    __tablename__ = "requisition_return_logs"

    id = Column(Integer, primary_key=True, index=True)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, comment="归还数量")
    physical_stock_before = Column(Integer, nullable=False, comment="归还前设备库存")
    physical_stock_after = Column(Integer, nullable=False, comment="归还后设备库存")
    remark = Column(Text, comment="备注")
    returned_at = Column(DateTime(timezone=True), server_default=func.now(), comment="归还时间")
    requisitioner_name = Column(String(100), nullable=False, comment="归还人（领用时记录的领用人）")
    operator_name = Column(String(100), nullable=True, comment="操作人（系统登录用户）")

    def __repr__(self):
        return f"<RequisitionReturnLog(id={self.id}, spare_part_id={self.spare_part_id}, quantity={self.quantity})>"
