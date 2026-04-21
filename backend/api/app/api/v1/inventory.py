# app/api/v1/inventory.py
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.core.database import get_db
from app.core.datetime_utils import beijing_date_range_to_utc_naive
from app.api.v1.auth import get_current_user, _user_material_scopes
from app.models.user import User
from app.crud.inventory import get_inventory_records, get_inventory_operator_options
from app.schemas.inventory import InventoryRecordResponse

router = APIRouter()

MaterialScope = Literal["electrical", "mechanical"]


@router.get("/inventory/test")
async def inventory_test():
    return {"message": "库存管理模块已实现"}


@router.get("/inventory/records", response_model=list[InventoryRecordResponse])
async def list_inventory_records(
    scope: MaterialScope = Query(..., description="物资范围：electrical 仅电气，mechanical 仅机械"),
    time_range: str = Query("30d", description="时间范围: today | 7d | 30d | 6m | 1y | custom"),
    start_date: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD，time_range=custom 时必填"),
    end_date: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD，time_range=custom 时必填"),
    event_type: Optional[str] = Query(None, description="事件类型：领用 | 入库 | 管理出库"),
    requisitioner: Optional[str] = Query(None, description="领用人姓名（模糊匹配）"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询库存记录，仅返回指定 scope（电气或机械）的数据，电气/机械数据不交叉。"""
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

    records = get_inventory_records(
        db,
        material_scope=scope,
        time_range=time_range,
        start_date=start_dt,
        end_date=end_dt,
        event_type=event_type,
        requisitioner_name=requisitioner,
    )
    return records


@router.get("/inventory/operator-options")
async def list_inventory_operator_options(
    scope: MaterialScope = Query(..., description="物资范围：electrical | mechanical"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取库存记录中已出现的操作人列表，按 scope 仅电气或仅机械。"""
    allowed = _user_material_scopes(current_user)
    if scope not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该物资类型的访问权限")
    return get_inventory_operator_options(db, material_scope=scope)
