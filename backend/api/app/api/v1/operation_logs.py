from datetime import datetime
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.datetime_utils import beijing_date_range_to_utc_naive
from app.api.v1.auth import get_current_user, _user_material_scopes
from app.models.user import User
from app.crud.operation_log import get_operation_logs, get_operation_logs_count, get_operation_log_operator_options
from app.schemas.operation_log import OperationLogListResponse, OperationLogResponse

router = APIRouter()

MaterialScope = Literal["electrical", "mechanical"]


@router.get("/operation-logs", response_model=OperationLogListResponse, tags=["操作记录"])
async def list_operation_logs(
    scope: MaterialScope = Query(..., description="物资范围：electrical 仅电气备件/领用记录，mechanical 仅机械备件/领用记录"),
    time_range: str = Query("30d", description="时间范围: today | 7d | 30d | 6m | 1y | custom"),
    start_date: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD，time_range=custom 时必填"),
    end_date: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD，time_range=custom 时必填"),
    username: Optional[str] = Query(None, description="按操作人用户名过滤"),
    module: Optional[str] = Query(None, description="按业务模块过滤"),
    action: Optional[str] = Query(None, description="按操作类型过滤，如 create / update / delete / requisition 等"),
    keyword: Optional[str] = Query(None, description="按摘要关键字模糊搜索"),
    limit: int = Query(20, ge=1, le=500, description="每页条数，默认20，可选50/100等"),
    skip: int = Query(0, ge=0, description="跳过条数，用于分页"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询操作记录，仅返回指定 scope（电气或机械）的备件/领用相关日志；返回当前页 data 与总条数 total，支持 limit/skip 分页。"""
    allowed = _user_material_scopes(current_user)
    if scope not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该物资类型的访问权限")
    start_dt = None
    end_dt = None
    if time_range == "custom" and start_date and end_date:
        try:
            start_dt, end_dt = beijing_date_range_to_utc_naive(start_date, end_date)
        except ValueError:
            start_dt = end_dt = None
        if start_dt is None or end_dt is None:
            time_range = "30d"

    total = get_operation_logs_count(
        db,
        material_scope=scope,
        time_range=time_range,
        start_date=start_dt,
        end_date=end_dt,
        username=username,
        module=module,
        action=action,
        keyword=keyword,
    )
    logs = get_operation_logs(
        db,
        material_scope=scope,
        time_range=time_range,
        start_date=start_dt,
        end_date=end_dt,
        username=username,
        module=module,
        action=action,
        keyword=keyword,
        limit=limit,
        skip=skip,
    )
    return OperationLogListResponse(data=logs, total=total)


@router.get("/operation-logs/operator-options", tags=["操作记录"])
async def list_operation_log_operator_options(
    scope: MaterialScope = Query(..., description="物资范围：electrical | mechanical"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取操作日志中已出现的操作人列表，按 scope 仅电气或仅机械。"""
    allowed = _user_material_scopes(current_user)
    if scope not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该物资类型的访问权限")
    return get_operation_log_operator_options(db, material_scope=scope)

