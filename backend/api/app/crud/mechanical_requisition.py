# app/crud/mechanical_requisition.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List, Dict, Any

from app.models.mechanical_spare_part import MechanicalSparePart
from app.models.mechanical_requisition_log import MechanicalRequisitionLog
from app.models.mechanical_requisition_return_log import MechanicalRequisitionReturnLog


def requisition_mechanical_spare_part(
    db: Session,
    mechanical_spare_part_id: int,
    quantity: int,
    requisitioner_name: str,
    remark: Optional[str] = None,
    operator_name: Optional[str] = None,
    requisition_reason: Optional[str] = None,
    usage_location: Optional[str] = None,
) -> Optional[dict]:
    item = db.query(MechanicalSparePart).filter(MechanicalSparePart.id == mechanical_spare_part_id).first()
    if not item:
        return None
    stock_before = item.physical_stock or 0
    if quantity <= 0 or stock_before < quantity:
        return None
    stock_after = stock_before - quantity
    item.physical_stock = stock_after
    # 只传入模型上存在的列，兼容工厂未更新 models/mechanical_requisition_log.py 的旧部署
    log_attrs = {
        "mechanical_spare_part_id": mechanical_spare_part_id,
        "quantity": quantity,
        "physical_stock_before": stock_before,
        "physical_stock_after": stock_after,
        "remark": remark or None,
        "requisitioner_name": (requisitioner_name or "").strip() or "—",
        "operator_name": operator_name,
        "requisition_reason": (requisition_reason or "").strip() or None,
        "usage_location": (usage_location or "").strip() or None,
    }
    model_keys = {c.key for c in MechanicalRequisitionLog.__table__.columns}
    log_kw = {k: v for k, v in log_attrs.items() if k in model_keys}
    log = MechanicalRequisitionLog(**log_kw)
    db.add(log)
    db.commit()
    db.refresh(item)
    return {
        "success": True,
        "message": "领用成功",
        "spare_part_id": mechanical_spare_part_id,
        "quantity": quantity,
        "physical_stock_before": stock_before,
        "physical_stock_after": stock_after,
    }


def get_unreturned_quantity_mechanical(db: Session, mechanical_spare_part_id: int, operator_name: str) -> int:
    """计算当前用户对指定机械备件的未归还数量。"""
    name = (operator_name or "").strip()
    if not name:
        return 0
    requisitioned = db.query(func.coalesce(func.sum(MechanicalRequisitionLog.quantity), 0)).filter(
        MechanicalRequisitionLog.mechanical_spare_part_id == mechanical_spare_part_id,
        (MechanicalRequisitionLog.operator_name == name) | (MechanicalRequisitionLog.requisitioner_name == name),
    ).scalar() or 0
    returned = db.query(func.coalesce(func.sum(MechanicalRequisitionReturnLog.quantity), 0)).filter(
        MechanicalRequisitionReturnLog.mechanical_spare_part_id == mechanical_spare_part_id,
        (MechanicalRequisitionReturnLog.operator_name == name) | (MechanicalRequisitionReturnLog.requisitioner_name == name),
    ).scalar() or 0
    return max(0, int(requisitioned) - int(returned))


def return_mechanical_spare_part(
    db: Session,
    mechanical_spare_part_id: int,
    quantity: int,
    requisitioner_name: str,
    remark: Optional[str] = None,
    operator_name: Optional[str] = None,
) -> Optional[dict]:
    """归还机械备件：增加库存并记录归还日志。归还数量不能超过当前用户的未归还余量。"""
    if quantity <= 0:
        return None
    name = (operator_name or requisitioner_name or "").strip()
    unreturned = get_unreturned_quantity_mechanical(db, mechanical_spare_part_id, name)
    if quantity > unreturned:
        return None
    item = db.query(MechanicalSparePart).filter(MechanicalSparePart.id == mechanical_spare_part_id).first()
    if not item:
        return None
    stock_before = item.physical_stock or 0
    stock_after = stock_before + quantity
    item.physical_stock = stock_after
    log = MechanicalRequisitionReturnLog(
        mechanical_spare_part_id=mechanical_spare_part_id,
        quantity=quantity,
        physical_stock_before=stock_before,
        physical_stock_after=stock_after,
        remark=remark or None,
        requisitioner_name=(requisitioner_name or "").strip() or "—",
        operator_name=operator_name,
    )
    db.add(log)
    db.commit()
    db.refresh(item)
    return {
        "success": True,
        "message": "归还成功",
        "spare_part_id": mechanical_spare_part_id,
        "quantity": quantity,
        "physical_stock_before": stock_before,
        "physical_stock_after": stock_after,
    }


def get_recent_mechanical_requisition_logs(
    db: Session,
    operator_name: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """当前用户的最近领用记录（机械），按领用时间倒序。附带该备件的未归还数量。"""
    if not operator_name or not str(operator_name).strip():
        return []
    name = str(operator_name).strip()
    logs = (
        db.query(MechanicalRequisitionLog)
        .filter(
            (MechanicalRequisitionLog.operator_name == name) | (MechanicalRequisitionLog.requisitioner_name == name)
        )
        .order_by(desc(MechanicalRequisitionLog.requisition_at))
        .limit(limit)
        .all()
    )
    out = []
    for log in logs:
        part = db.query(MechanicalSparePart).filter(MechanicalSparePart.id == log.mechanical_spare_part_id).first()
        unreturned = get_unreturned_quantity_mechanical(db, log.mechanical_spare_part_id, name)
        out.append({
            "id": log.id,
            "requisition_at": log.requisition_at.isoformat() if hasattr(log.requisition_at, "isoformat") else str(log.requisition_at),
            "quantity": log.quantity,
            "mechanical_spare_part_id": log.mechanical_spare_part_id,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "location_code": part.location_code if part else None,
            "unreturned_qty": unreturned,
        })
    return out
