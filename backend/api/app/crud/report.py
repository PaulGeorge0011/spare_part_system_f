# app/crud/report.py
"""
报表统计：按品牌、适用机型统计入库、出库数量；按 material_scope 仅电气或仅机械，数据不交叉。
出库包括：领用 + 管理出库
"""
from datetime import datetime, timedelta
from typing import Any, List, Optional, Literal

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.core.datetime_utils import utc_now
from app.models.requisition_log import RequisitionLog
from app.models.inbound_log import InboundLog
from app.models.outbound_log import OutboundLog
from app.models.spare_part import SparePart
from app.models.mechanical_requisition_log import MechanicalRequisitionLog
from app.models.mechanical_inbound_log import MechanicalInboundLog
from app.models.mechanical_outbound_log import MechanicalOutboundLog
from app.models.mechanical_spare_part import MechanicalSparePart

MaterialScope = Literal["electrical", "mechanical"]


def _get_time_range(
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


def _normalize_label(val: Any) -> str:
    if val is None or (isinstance(val, str) and not val.strip()):
        return "未分类"
    return str(val).strip() or "未分类"


def get_report_statistics_by_brand(
    db: Session,
    material_scope: MaterialScope,
    time_range: str = "30d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[dict]:
    """按品牌统计入库、出库数量，仅统计指定 scope（电气或机械）数据。"""
    start, end = _get_time_range(time_range, start_date, end_date)
    agg: dict[str, dict] = {}

    if material_scope == "electrical":
        _agg_brand_electrical(db, start, end, agg)
    else:
        _agg_brand_mechanical(db, start, end, agg)

    result = sorted(agg.values(), key=lambda x: x["brand"])
    return result


def _agg_brand_electrical(db: Session, start: datetime, end: datetime, agg: dict) -> None:
    q_in = (
        db.query(SparePart.brand, func.sum(InboundLog.quantity).label("total"))
        .join(InboundLog, InboundLog.spare_part_id == SparePart.id)
        .filter(and_(InboundLog.inbound_at >= start, InboundLog.inbound_at <= end))
        .group_by(SparePart.brand)
    )
    for row in q_in.all():
        brand = _normalize_label(row.brand)
        if brand not in agg:
            agg[brand] = {"brand": brand, "inbound": 0, "outbound": 0}
        agg[brand]["inbound"] += int(row.total or 0)
    q_req = (
        db.query(SparePart.brand, func.sum(RequisitionLog.quantity).label("total"))
        .join(RequisitionLog, RequisitionLog.spare_part_id == SparePart.id)
        .filter(and_(RequisitionLog.requisition_at >= start, RequisitionLog.requisition_at <= end))
        .group_by(SparePart.brand)
    )
    for row in q_req.all():
        brand = _normalize_label(row.brand)
        if brand not in agg:
            agg[brand] = {"brand": brand, "inbound": 0, "outbound": 0}
        agg[brand]["outbound"] += int(row.total or 0)
    q_out = (
        db.query(SparePart.brand, func.sum(OutboundLog.quantity).label("total"))
        .join(OutboundLog, OutboundLog.spare_part_id == SparePart.id)
        .filter(and_(OutboundLog.outbound_at >= start, OutboundLog.outbound_at <= end))
        .group_by(SparePart.brand)
    )
    for row in q_out.all():
        brand = _normalize_label(row.brand)
        if brand not in agg:
            agg[brand] = {"brand": brand, "inbound": 0, "outbound": 0}
        agg[brand]["outbound"] += int(row.total or 0)


def _agg_brand_mechanical(db: Session, start: datetime, end: datetime, agg: dict) -> None:
    q_in = (
        db.query(MechanicalSparePart.brand, func.sum(MechanicalInboundLog.quantity).label("total"))
        .join(MechanicalInboundLog, MechanicalInboundLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalInboundLog.inbound_at >= start, MechanicalInboundLog.inbound_at <= end))
        .group_by(MechanicalSparePart.brand)
    )
    for row in q_in.all():
        brand = _normalize_label(row.brand)
        if brand not in agg:
            agg[brand] = {"brand": brand, "inbound": 0, "outbound": 0}
        agg[brand]["inbound"] += int(row.total or 0)
    q_req = (
        db.query(MechanicalSparePart.brand, func.sum(MechanicalRequisitionLog.quantity).label("total"))
        .join(MechanicalRequisitionLog, MechanicalRequisitionLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalRequisitionLog.requisition_at >= start, MechanicalRequisitionLog.requisition_at <= end))
        .group_by(MechanicalSparePart.brand)
    )
    for row in q_req.all():
        brand = _normalize_label(row.brand)
        if brand not in agg:
            agg[brand] = {"brand": brand, "inbound": 0, "outbound": 0}
        agg[brand]["outbound"] += int(row.total or 0)
    q_out = (
        db.query(MechanicalSparePart.brand, func.sum(MechanicalOutboundLog.quantity).label("total"))
        .join(MechanicalOutboundLog, MechanicalOutboundLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalOutboundLog.outbound_at >= start, MechanicalOutboundLog.outbound_at <= end))
        .group_by(MechanicalSparePart.brand)
    )
    for row in q_out.all():
        brand = _normalize_label(row.brand)
        if brand not in agg:
            agg[brand] = {"brand": brand, "inbound": 0, "outbound": 0}
        agg[brand]["outbound"] += int(row.total or 0)


def get_report_statistics_by_applicable_model(
    db: Session,
    material_scope: MaterialScope,
    time_range: str = "30d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[dict]:
    """按适用机型统计入库、出库数量，仅统计指定 scope（电气或机械）数据。"""
    start, end = _get_time_range(time_range, start_date, end_date)
    agg: dict[str, dict] = {}

    if material_scope == "electrical":
        _agg_model_electrical(db, start, end, agg)
    else:
        _agg_model_mechanical(db, start, end, agg)

    result = sorted(agg.values(), key=lambda x: x["applicable_model"])
    return result


def _agg_model_electrical(db: Session, start: datetime, end: datetime, agg: dict) -> None:
    q_in = (
        db.query(SparePart.applicable_model, func.sum(InboundLog.quantity).label("total"))
        .join(InboundLog, InboundLog.spare_part_id == SparePart.id)
        .filter(and_(InboundLog.inbound_at >= start, InboundLog.inbound_at <= end))
        .group_by(SparePart.applicable_model)
    )
    for row in q_in.all():
        model = _normalize_label(row.applicable_model)
        if model not in agg:
            agg[model] = {"applicable_model": model, "inbound": 0, "outbound": 0}
        agg[model]["inbound"] += int(row.total or 0)
    q_req = (
        db.query(SparePart.applicable_model, func.sum(RequisitionLog.quantity).label("total"))
        .join(RequisitionLog, RequisitionLog.spare_part_id == SparePart.id)
        .filter(and_(RequisitionLog.requisition_at >= start, RequisitionLog.requisition_at <= end))
        .group_by(SparePart.applicable_model)
    )
    for row in q_req.all():
        model = _normalize_label(row.applicable_model)
        if model not in agg:
            agg[model] = {"applicable_model": model, "inbound": 0, "outbound": 0}
        agg[model]["outbound"] += int(row.total or 0)
    q_out = (
        db.query(SparePart.applicable_model, func.sum(OutboundLog.quantity).label("total"))
        .join(OutboundLog, OutboundLog.spare_part_id == SparePart.id)
        .filter(and_(OutboundLog.outbound_at >= start, OutboundLog.outbound_at <= end))
        .group_by(SparePart.applicable_model)
    )
    for row in q_out.all():
        model = _normalize_label(row.applicable_model)
        if model not in agg:
            agg[model] = {"applicable_model": model, "inbound": 0, "outbound": 0}
        agg[model]["outbound"] += int(row.total or 0)


def _agg_model_mechanical(db: Session, start: datetime, end: datetime, agg: dict) -> None:
    q_in = (
        db.query(MechanicalSparePart.applicable_model, func.sum(MechanicalInboundLog.quantity).label("total"))
        .join(MechanicalInboundLog, MechanicalInboundLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalInboundLog.inbound_at >= start, MechanicalInboundLog.inbound_at <= end))
        .group_by(MechanicalSparePart.applicable_model)
    )
    for row in q_in.all():
        model = _normalize_label(row.applicable_model)
        if model not in agg:
            agg[model] = {"applicable_model": model, "inbound": 0, "outbound": 0}
        agg[model]["inbound"] += int(row.total or 0)
    q_req = (
        db.query(MechanicalSparePart.applicable_model, func.sum(MechanicalRequisitionLog.quantity).label("total"))
        .join(MechanicalRequisitionLog, MechanicalRequisitionLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalRequisitionLog.requisition_at >= start, MechanicalRequisitionLog.requisition_at <= end))
        .group_by(MechanicalSparePart.applicable_model)
    )
    for row in q_req.all():
        model = _normalize_label(row.applicable_model)
        if model not in agg:
            agg[model] = {"applicable_model": model, "inbound": 0, "outbound": 0}
        agg[model]["outbound"] += int(row.total or 0)
    q_out = (
        db.query(MechanicalSparePart.applicable_model, func.sum(MechanicalOutboundLog.quantity).label("total"))
        .join(MechanicalOutboundLog, MechanicalOutboundLog.mechanical_spare_part_id == MechanicalSparePart.id)
        .filter(and_(MechanicalOutboundLog.outbound_at >= start, MechanicalOutboundLog.outbound_at <= end))
        .group_by(MechanicalSparePart.applicable_model)
    )
    for row in q_out.all():
        model = _normalize_label(row.applicable_model)
        if model not in agg:
            agg[model] = {"applicable_model": model, "inbound": 0, "outbound": 0}
        agg[model]["outbound"] += int(row.total or 0)
