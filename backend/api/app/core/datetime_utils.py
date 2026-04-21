# app/core/datetime_utils.py
"""
统一时间处理：后端内部使用 UTC，API 返回带 Z 的 ISO 时间，
前端按北京时间（UTC+8）展示。
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# 北京时间 UTC+8
BEIJING_TZ = timezone(offset=timedelta(hours=8))


def utc_now() -> datetime:
    """返回当前 UTC 时间（带 tzinfo），用于写入 DB 与业务逻辑。"""
    return datetime.now(timezone.utc)


def ensure_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    若 datetime 为 naive（无 tzinfo），视为 UTC 并加上 tzinfo。
    用于从 DB 读出的时间在返回 API 前统一为带 Z 的 UTC。
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


def to_beijing(dt: Optional[datetime]) -> Optional[datetime]:
    """将 datetime 转为北京时间（UTC+8）。若为 naive 则先视为 UTC。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ)


def beijing_date_range_to_utc_naive(start_date_str: str, end_date_str: str) -> tuple[datetime, datetime]:
    """
    将前端传入的日期字符串（视为北京时间日期）转为 UTC naive 的起止时间，用于 DB 查询。
    这样用户选择「某日」时按北京时间的当天 00:00 ~ 23:59:59 查询。
    """
    start_naive = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_naive = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=999999
    )
    start_beijing = start_naive.replace(tzinfo=BEIJING_TZ)
    end_beijing = end_naive.replace(tzinfo=BEIJING_TZ)
    start_utc = start_beijing.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_beijing.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc
