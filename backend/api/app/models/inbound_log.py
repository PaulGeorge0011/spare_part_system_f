# app/models/inbound_log.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class InboundLog(Base):
    """入库记录（编辑表单中增加实物库存时产生）"""

    __tablename__ = "inbound_logs"

    id = Column(Integer, primary_key=True, index=True)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, comment="入库数量")
    physical_stock_before = Column(Integer, nullable=False, comment="入库前实物库存")
    physical_stock_after = Column(Integer, nullable=False, comment="入库后实物库存")
    remark = Column(Text, comment="备注")
    inbound_at = Column(DateTime(timezone=True), server_default=func.now(), comment="入库时间")
    operator_name = Column(String(100), nullable=True, comment="操作人")

    def __repr__(self):
        return f"<InboundLog(id={self.id}, spare_part_id={self.spare_part_id}, quantity={self.quantity})>"
