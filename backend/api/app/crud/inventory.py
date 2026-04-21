# app/crud/inventory.py
from datetime import datetime, timedelta
from typing import List, Optional, Literal

from app.core.datetime_utils import utc_now
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.requisition_log import RequisitionLog
from app.models.requisition_return_log import RequisitionReturnLog
from app.models.inbound_log import InboundLog
from app.models.outbound_log import OutboundLog
from app.models.spare_part import SparePart
from app.models.mechanical_requisition_log import MechanicalRequisitionLog
from app.models.mechanical_requisition_return_log import MechanicalRequisitionReturnLog
from app.models.mechanical_inbound_log import MechanicalInboundLog
from app.models.mechanical_outbound_log import MechanicalOutboundLog
from app.models.mechanical_spare_part import MechanicalSparePart

# id 偏移，避免不同事件类型的 id 冲突
INBOUND_ID_OFFSET = 1_000_000
OUTBOUND_ID_OFFSET = 2_000_000
RETURN_ID_OFFSET = 3_000_000

MaterialScope = Literal["electrical", "mechanical"]


def _get_time_bounds(
    time_range: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> tuple[datetime, datetime]:
    now = utc_now().replace(tzinfo=None)
    if time_range == "today":
        start = datetime(now.year, now.month, now.day)
        end = now
    elif time_range == "7d":
        start = now - timedelta(days=7)
        end = now
    elif time_range == "30d":
        start = now - timedelta(days=30)
        end = now
    elif time_range == "6m":
        start = now - timedelta(days=180)
        end = now
    elif time_range == "1y":
        start = now - timedelta(days=365)
        end = now
    elif time_range == "custom" and start_date is not None and end_date is not None:
        start, end = start_date, end_date
    else:
        start = now - timedelta(days=30)
        end = now
    return start, end


def get_inventory_records(
    db: Session,
    material_scope: MaterialScope,
    time_range: str = "30d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[str] = None,
    requisitioner_name: Optional[str] = None,
) -> List[dict]:
    """
    按时间范围查询库存记录（领用、入库、管理出库等），按 material_scope 仅查电气或仅查机械。
    """
    start, end = _get_time_bounds(time_range, start_date, end_date)
    result: List[dict] = []

    if material_scope == "electrical":
        _append_electrical_records(db, start, end, result)
    else:
        _append_mechanical_records(db, start, end, result)

    if event_type and event_type.strip():
        et = event_type.strip()
        result = [r for r in result if r.get("event_type") == et]
    if requisitioner_name and requisitioner_name.strip():
        kw = requisitioner_name.strip()
        result = [
            r for r in result
            if (r.get("requisitioner_name") and kw in str(r["requisitioner_name"]))
            or (r.get("operator_name") and kw in str(r["operator_name"]))
        ]

    def _sort_key(r):
        t = r.get("_sort_time")
        if t is None:
            return (0, 0.0)
        try:
            return (1, -t.timestamp())
        except Exception:
            return (1, 0.0)
    result.sort(key=_sort_key)
    for r in result:
        r.pop("_sort_time", None)
    return result


def _append_electrical_records(db: Session, start: datetime, end: datetime, result: List[dict]) -> None:
    q_req = (
        db.query(RequisitionLog, SparePart)
        .join(SparePart, RequisitionLog.spare_part_id == SparePart.id)
        .filter(
            and_(
                RequisitionLog.requisition_at >= start,
                RequisitionLog.requisition_at <= end,
            )
        )
    )
    for log, part in q_req.all():
        result.append({
            "id": log.id,
            "event_type": "领用",
            "inbound_time": None,
            "outbound_time": log.requisition_at,
            "requisitioner_name": getattr(log, "requisitioner_name", None) or None,
            "operator_name": log.operator_name,
            "spare_part_id": log.spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": getattr(log, "requisition_reason", None),
            "usage_location": getattr(log, "usage_location", None),
            "_sort_time": log.requisition_at,
        })
    q_ret = (
        db.query(RequisitionReturnLog, SparePart)
        .join(SparePart, RequisitionReturnLog.spare_part_id == SparePart.id)
        .filter(and_(RequisitionReturnLog.returned_at >= start, RequisitionReturnLog.returned_at <= end))
    )
    for log, part in q_ret.all():
        result.append({
            "id": RETURN_ID_OFFSET + log.id,
            "event_type": "归还",
            "inbound_time": log.returned_at,
            "outbound_time": None,
            "requisitioner_name": log.requisitioner_name,
            "operator_name": log.operator_name,
            "spare_part_id": log.spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": None,
            "usage_location": None,
            "_sort_time": log.returned_at,
        })
    q_in = (
        db.query(InboundLog, SparePart)
        .join(SparePart, InboundLog.spare_part_id == SparePart.id)
        .filter(and_(InboundLog.inbound_at >= start, InboundLog.inbound_at <= end))
    )
    for log, part in q_in.all():
        result.append({
            "id": INBOUND_ID_OFFSET + log.id,
            "event_type": "入库",
            "inbound_time": log.inbound_at,
            "outbound_time": None,
            "requisitioner_name": None,
            "operator_name": log.operator_name,
            "spare_part_id": log.spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": None,
            "usage_location": None,
            "_sort_time": log.inbound_at,
        })
    q_out = (
        db.query(OutboundLog, SparePart)
        .join(SparePart, OutboundLog.spare_part_id == SparePart.id)
        .filter(and_(OutboundLog.outbound_at >= start, OutboundLog.outbound_at <= end))
    )
    for log, part in q_out.all():
        result.append({
            "id": OUTBOUND_ID_OFFSET + log.id,
            "event_type": "管理出库",
            "inbound_time": None,
            "outbound_time": log.outbound_at,
            "requisitioner_name": None,
            "operator_name": log.operator_name,
            "spare_part_id": log.spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": None,
            "usage_location": None,
            "_sort_time": log.outbound_at,
        })


def _append_mechanical_records(db: Session, start: datetime, end: datetime, result: List[dict]) -> None:
    q_req = (
        db.query(MechanicalRequisitionLog, MechanicalSparePart)
        .join(MechanicalSparePart, MechanicalRequisitionLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(
            and_(
                MechanicalRequisitionLog.requisition_at >= start,
                MechanicalRequisitionLog.requisition_at <= end,
            )
        )
    )
    for log, part in q_req.all():
        result.append({
            "id": log.id,
            "event_type": "领用",
            "inbound_time": None,
            "outbound_time": log.requisition_at,
            "requisitioner_name": getattr(log, "requisitioner_name", None) or None,
            "operator_name": log.operator_name,
            "spare_part_id": log.mechanical_spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": getattr(log, "requisition_reason", None),
            "usage_location": getattr(log, "usage_location", None),
            "_sort_time": log.requisition_at,
        })
    q_ret = (
        db.query(MechanicalRequisitionReturnLog, MechanicalSparePart)
        .join(MechanicalSparePart, MechanicalRequisitionReturnLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalRequisitionReturnLog.returned_at >= start, MechanicalRequisitionReturnLog.returned_at <= end))
    )
    for log, part in q_ret.all():
        result.append({
            "id": RETURN_ID_OFFSET + log.id,
            "event_type": "归还",
            "inbound_time": log.returned_at,
            "outbound_time": None,
            "requisitioner_name": log.requisitioner_name,
            "operator_name": log.operator_name,
            "spare_part_id": log.mechanical_spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": None,
            "usage_location": None,
            "_sort_time": log.returned_at,
        })
    q_in = (
        db.query(MechanicalInboundLog, MechanicalSparePart)
        .join(MechanicalSparePart, MechanicalInboundLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalInboundLog.inbound_at >= start, MechanicalInboundLog.inbound_at <= end))
    )
    for log, part in q_in.all():
        result.append({
            "id": INBOUND_ID_OFFSET + log.id,
            "event_type": "入库",
            "inbound_time": log.inbound_at,
            "outbound_time": None,
            "requisitioner_name": None,
            "operator_name": log.operator_name,
            "spare_part_id": log.mechanical_spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": None,
            "usage_location": None,
            "_sort_time": log.inbound_at,
        })
    q_out = (
        db.query(MechanicalOutboundLog, MechanicalSparePart)
        .join(MechanicalSparePart, MechanicalOutboundLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalOutboundLog.outbound_at >= start, MechanicalOutboundLog.outbound_at <= end))
    )
    for log, part in q_out.all():
        result.append({
            "id": OUTBOUND_ID_OFFSET + log.id,
            "event_type": "管理出库",
            "inbound_time": None,
            "outbound_time": log.outbound_at,
            "requisitioner_name": None,
            "operator_name": log.operator_name,
            "spare_part_id": log.mechanical_spare_part_id,
            "location_code": part.location_code if part else None,
            "storage_location": part.storage_location if part else None,
            "mes_material_code": part.mes_material_code if part else None,
            "specification_model": part.specification_model if part else None,
            "unit": part.unit if part else None,
            "physical_image_url": part.physical_image_url if part else None,
            "physical_image_url2": part.physical_image_url2 if part else None,
            "quantity": log.quantity,
            "physical_stock_before": log.physical_stock_before,
            "physical_stock_after": log.physical_stock_after,
            "remark": log.remark,
            "requisition_reason": None,
            "usage_location": None,
            "_sort_time": log.outbound_at,
        })


def get_inventory_operator_options(db: Session, material_scope: MaterialScope) -> List[str]:
    """获取库存记录中已出现的操作人列表，按 material_scope 仅电气或仅机械"""
    seen: set[str] = set()
    options: List[str] = []

    if material_scope == "electrical":
        for (name,) in db.query(RequisitionLog.requisitioner_name).filter(
            RequisitionLog.requisitioner_name.isnot(None),
            RequisitionLog.requisitioner_name != "",
        ).distinct().all():
            n = (name or "").strip()
            if n and n not in seen:
                seen.add(n)
                options.append(n)
        for model in (RequisitionLog, InboundLog, OutboundLog):
            col = getattr(model, "operator_name", None)
            if col is None:
                continue
            for (name,) in db.query(col).filter(col.isnot(None), col != "").distinct().all():
                n = (name or "").strip()
                if n and n not in seen:
                    seen.add(n)
                    options.append(n)
    else:
        for (name,) in db.query(MechanicalRequisitionLog.requisitioner_name).filter(
            MechanicalRequisitionLog.requisitioner_name.isnot(None),
            MechanicalRequisitionLog.requisitioner_name != "",
        ).distinct().all():
            n = (name or "").strip()
            if n and n not in seen:
                seen.add(n)
                options.append(n)
        for model in (MechanicalRequisitionLog, MechanicalInboundLog, MechanicalOutboundLog):
            col = getattr(model, "operator_name", None)
            if col is None:
                continue
            for (name,) in db.query(col).filter(col.isnot(None), col != "").distinct().all():
                n = (name or "").strip()
                if n and n not in seen:
                    seen.add(n)
                    options.append(n)

    return sorted(options)
