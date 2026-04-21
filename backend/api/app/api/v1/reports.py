# app/api/v1/reports.py
from typing import Optional, Literal

from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.core.database import get_db
from app.core.datetime_utils import beijing_date_range_to_utc_naive
from app.api.v1.auth import get_current_user, _user_material_scopes
from app.models.user import User
from app.crud.report import (
    get_report_statistics_by_brand,
    get_report_statistics_by_applicable_model,
)

router = APIRouter()

MaterialScope = Literal["electrical", "mechanical"]


@router.get("/reports/statistics/by-brand")
async def report_statistics_by_brand(
    scope: MaterialScope = Query(..., description="物资范围：electrical 仅电气，mechanical 仅机械"),
    time_range: str = Query("30d", description="时间范围: today | 7d | 30d | 6m | 1y | custom"),
    start_date: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按品牌统计入库、出库数量，仅统计指定 scope 数据，电气/机械不交叉。"""
    allowed = _user_material_scopes(current_user)
    if scope not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该物资类型的访问权限")
    start_dt = end_dt = None
    if time_range == "custom" and start_date and end_date:
        try:
            start_dt, end_dt = beijing_date_range_to_utc_naive(start_date, end_date)
        except ValueError:
            time_range = "30d"
    return get_report_statistics_by_brand(
        db,
        material_scope=scope,
        time_range=time_range,
        start_date=start_dt,
        end_date=end_dt,
    )


@router.get("/reports/statistics/by-applicable-model")
async def report_statistics_by_applicable_model(
    scope: MaterialScope = Query(..., description="物资范围：electrical | mechanical"),
    time_range: str = Query("30d", description="时间范围: today | 7d | 30d | 6m | 1y | custom"),
    start_date: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按适用机型统计入库、出库数量，仅统计指定 scope 数据，电气/机械不交叉。"""
    allowed = _user_material_scopes(current_user)
    if scope not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该物资类型的访问权限")
    start_dt = end_dt = None
    if time_range == "custom" and start_date and end_date:
        try:
            start_dt, end_dt = beijing_date_range_to_utc_naive(start_date, end_date)
        except ValueError:
            time_range = "30d"
    return get_report_statistics_by_applicable_model(
        db,
        material_scope=scope,
        time_range=time_range,
        start_date=start_dt,
        end_date=end_dt,
    )
