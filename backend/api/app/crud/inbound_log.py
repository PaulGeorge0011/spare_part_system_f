# app/crud/inbound_log.py
from sqlalchemy.orm import Session

from app.models.inbound_log import InboundLog


def create_inbound_log(
    db: Session,
    spare_part_id: int,
    quantity: int,
    physical_stock_before: int,
    physical_stock_after: int,
    operator_name: str | None = None,
    remark: str | None = None,
):
    """写入一条入库记录（编辑表单中增加实物库存时调用）"""
    log = InboundLog(
        spare_part_id=spare_part_id,
        quantity=quantity,
        physical_stock_before=physical_stock_before,
        physical_stock_after=physical_stock_after,
        operator_name=operator_name,
        remark=remark,
    )
    db.add(log)
    db.flush()
    return log
