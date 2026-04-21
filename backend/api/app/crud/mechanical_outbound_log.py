# app/crud/mechanical_outbound_log.py
from sqlalchemy.orm import Session

from app.models.mechanical_outbound_log import MechanicalOutboundLog


def create_mechanical_outbound_log(
    db: Session,
    mechanical_spare_part_id: int,
    quantity: int,
    physical_stock_before: int,
    physical_stock_after: int,
    operator_name: str | None = None,
    remark: str | None = None,
):
    log = MechanicalOutboundLog(
        mechanical_spare_part_id=mechanical_spare_part_id,
        quantity=quantity,
        physical_stock_before=physical_stock_before,
        physical_stock_after=physical_stock_after,
        operator_name=operator_name,
        remark=remark,
    )
    db.add(log)
    db.flush()
    return log
