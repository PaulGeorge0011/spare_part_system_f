from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.datetime_utils import utc_now
from app.models.operation_log import OperationLog
from app.models.user import User


def log_operation(
    db: Session,
    user: Optional[User],
    module: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    summary: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """
    写入一条操作日志。
    """
    real_name = getattr(user, "real_name", None) if user else None
    log = OperationLog(
        user_id=getattr(user, "id", None),
        username=getattr(user, "username", None),
        real_name=real_name,
        module=module,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        detail=detail,
    )
    db.add(log)
    # 交由调用方控制事务，这里不 commit


# 电气备件/领用相关操作日志 module；机械备件/领用为 mechanical_spare_part
MODULE_ELECTRICAL = "spare_part"
MODULE_MECHANICAL = "mechanical_spare_part"


def get_operation_logs(
    db: Session,
    material_scope: str,
    time_range: str = "30d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    username: Optional[str] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
) -> List[OperationLog]:
    """
    查询操作日志。material_scope 为 electrical 时仅查 spare_part 模块，mechanical 时仅查 mechanical_spare_part，电气/机械数据不交叉。
    """
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
        start = start_date
        end = end_date
    else:
        start = now - timedelta(days=30)
        end = now

    scope_module = MODULE_ELECTRICAL if material_scope == "electrical" else MODULE_MECHANICAL
    q = db.query(OperationLog).filter(
        and_(
            OperationLog.created_at >= start,
            OperationLog.created_at <= end,
            OperationLog.module == scope_module,
        )
    )

    if username:
        q = q.filter(OperationLog.username == username)
    if module:
        q = q.filter(OperationLog.module == module)
    if action:
        q = q.filter(OperationLog.action == action)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(OperationLog.summary.ilike(like))

    return q.order_by(OperationLog.created_at.desc()).offset(skip).limit(max(1, min(limit, 500))).all()


def get_operation_logs_count(
    db: Session,
    material_scope: str,
    time_range: str = "30d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    username: Optional[str] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    keyword: Optional[str] = None,
) -> int:
    """与 get_operation_logs 相同筛选条件下的总条数（不分页）。"""
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
        start = start_date
        end = end_date
    else:
        start = now - timedelta(days=30)
        end = now

    scope_module = MODULE_ELECTRICAL if material_scope == "electrical" else MODULE_MECHANICAL
    q = db.query(OperationLog).filter(
        and_(
            OperationLog.created_at >= start,
            OperationLog.created_at <= end,
            OperationLog.module == scope_module,
        )
    )
    if username:
        q = q.filter(OperationLog.username == username)
    if module:
        q = q.filter(OperationLog.module == module)
    if action:
        q = q.filter(OperationLog.action == action)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(OperationLog.summary.ilike(like))
    return q.count()


def get_operation_log_operator_options(db: Session, material_scope: str) -> List[dict]:
    """获取操作日志中已出现的操作人列表，按 material_scope 仅电气或仅机械。"""
    scope_module = MODULE_ELECTRICAL if material_scope == "electrical" else MODULE_MECHANICAL
    rows = (
        db.query(OperationLog.username, OperationLog.real_name)
        .filter(
            OperationLog.username.isnot(None),
            OperationLog.username != "",
            OperationLog.module == scope_module,
        )
        .distinct()
        .all()
    )
    seen: set[str] = set()
    options: List[dict] = []
    for username, real_name in rows:
        u = (username or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        display = (real_name or "").strip() or u
        options.append({"username": u, "real_name": real_name or None, "display": display})
    options.sort(key=lambda x: (x["display"], x["username"]))
    return options

