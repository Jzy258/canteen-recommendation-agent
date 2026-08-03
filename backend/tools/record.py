from langchain_core.tools import tool
from db import get_db

db = get_db()


@tool
def record_meal(date: str, meal_time: str, dish_id: int, portion: float = 1.0) -> int:
    """Record a meal intake (pending confirmation). Returns record_id."""
    return db.add_meal_record(date, meal_time, dish_id, portion)


@tool
def confirm_record(record_id: int) -> bool:
    """Confirm a pending meal record."""
    return db.confirm_meal_record(record_id)


@tool
def reject_record(record_id: int) -> bool:
    """Reject a pending meal record."""
    return db.reject_meal_record(record_id)


@tool
def get_pending_records() -> list[dict]:
    """Get all pending meal records (awaiting HITL confirmation)."""
    return db.get_pending_records()


@tool
def get_pending_records_by_date(date: str, meal_time: str = "") -> list[dict]:
    """Get pending meal records filtered by date (and optional meal_time)."""
    return db.get_pending_records_by_date(date=date, meal_time=meal_time)


@tool
def get_pending_record(record_id: int) -> dict:
    """Get a single pending meal record by id."""
    return db.get_pending_record(record_id)


@tool
def confirm_records(record_ids: list[int]) -> int:
    """Confirm multiple pending meal records at once. Returns confirmed count."""
    return db.confirm_records(record_ids)


@tool
def reject_records(record_ids: list[int]) -> int:
    """Reject multiple pending meal records at once. Returns rejected count."""
    return db.reject_records(record_ids)


@tool
def get_daily_intake(date: str) -> list[dict]:
    """Get daily nutrition breakdown by meal_time."""
    return db.get_daily_nutrition(date)


@tool
def get_day_total(date: str) -> dict:
    """Get whole-day nutrition total."""
    return db.get_day_total(date)


@tool
def get_weekly_trend(end_date: str = "", days: int = 7) -> list[dict]:
    """Get daily nutrition totals for the last N days (missing days filled with zero)."""
    return db.get_weekly_trend(end_date=end_date, days=days)


@tool
def get_weekly_summary(start_date: str = "", end_date: str = "") -> dict:
    """Get weekly nutrition summary (total + days + dish count)."""
    return db.get_weekly_summary(start_date=start_date, end_date=end_date)