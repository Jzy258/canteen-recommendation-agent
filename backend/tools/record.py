from langchain_core.tools import tool


def _db():
    from db import get_db
    return get_db()


@tool
def record_meal(date: str, meal_time: str, dish_id: int, portion: float = 1.0) -> int:
    """记录一餐摄入（待确认状态），返回记录 id。"""
    return _db().add_meal_record(date, meal_time, dish_id, portion)


@tool
def confirm_record(record_id: int) -> bool:
    """确认一条待审批的摄入记录。"""
    return _db().confirm_meal_record(record_id)


@tool
def reject_record(record_id: int) -> bool:
    """拒绝一条待审批的摄入记录。"""
    return _db().reject_meal_record(record_id)


@tool
def get_pending_records() -> list[dict]:
    """获取全部待审批（HITL）的摄入记录。"""
    return _db().get_pending_records()


@tool
def get_pending_records_by_date(date: str, meal_time: str = "") -> list[dict]:
    """按日期（可选餐次）获取待审批摄入记录。"""
    return _db().get_pending_records_by_date(date=date, meal_time=meal_time)


@tool
def get_pending_record(record_id: int) -> dict:
    """按 id 查询单条待审批记录。"""
    return _db().get_pending_record(record_id)


@tool
def confirm_records(record_ids: list[int]) -> int:
    """批量确认多条待审批记录，返回实际确认条数。"""
    return _db().confirm_records(record_ids)


@tool
def reject_records(record_ids: list[int]) -> int:
    """批量拒绝多条待审批记录，返回实际拒绝条数。"""
    return _db().reject_records(record_ids)


@tool
def get_daily_intake(date: str) -> list[dict]:
    """获取某日按餐次拆分的营养摄入。"""
    return _db().get_daily_nutrition(date)


@tool
def get_day_total(date: str) -> dict:
    """获取某日全天营养合计。"""
    return _db().get_day_total(date)


@tool
def get_weekly_trend(end_date: str = "", days: int = 7) -> list[dict]:
    """获取最近 N 天每日营养合计（缺失日期补零，供趋势图）。"""
    return _db().get_weekly_trend(end_date=end_date, days=days)


@tool
def get_weekly_summary(start_date: str = "", end_date: str = "") -> dict:
    """获取周营养汇总（合计 + 天数 + 菜品数）。"""
    return _db().get_weekly_summary(start_date=start_date, end_date=end_date)