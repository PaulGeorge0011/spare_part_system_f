# app/models/outbound_log.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class OutboundLog(Base):
    """管理出库记录（编辑表单中减少实物库存时产生）"""

    __tablename__ = "outbound_logs"

    id = Column(Integer, primary_key=True, index=True)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, comment="出库数量")
    physical_stock_before = Column(Integer, nullable=False, comment="出库前实物库存")
    physical_stock_after = Column(Integer, nullable=False, comment="出库后实物库存")
    remark = Column(Text, comment="备注")
    outbound_at = Column(DateTime(timezone=True), server_default=func.now(), comment="出库时间")
    operator_name = Column(String(100), nullable=True, comment="操作人")

    def __repr__(self):
        return f"<OutboundLog(id={self.id}, spare_part_id={self.spare_part_id}, quantity={self.quantity})>"
