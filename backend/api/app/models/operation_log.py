from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from ..core.database import Base


class OperationLog(Base):
    """通用操作日志，用于记录对数据执行的关键操作。"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 操作人信息
    user_id = Column(Integer, nullable=True, index=True, comment="操作人用户ID")
    username = Column(String(100), nullable=True, index=True, comment="操作人用户名")
    real_name = Column(String(100), nullable=True, comment="操作人真实姓名")

    # 业务维度
    module = Column(String(50), nullable=False, index=True, comment="业务模块，如 spare_part / requisition / inventory 等")
    action = Column(String(50), nullable=False, index=True, comment="操作类型，如 create / update / delete / requisition 等")
    entity_type = Column(String(50), nullable=True, index=True, comment="实体类型，如 spare_part / requisition_log 等")
    entity_id = Column(Integer, nullable=True, index=True, comment="实体ID")

    # 描述信息
    summary = Column(String(255), nullable=True, comment="操作简要说明")
    detail = Column(Text, nullable=True, comment="操作详情（JSON字符串或文本）")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="操作时间")

    def __repr__(self) -> str:
        return f"<OperationLog(id={self.id}, module={self.module}, action={self.action}, username={self.username})>"

