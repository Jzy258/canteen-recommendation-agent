import csv
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_ROOT / "backend"))

from db import SQLiteDatabase
from tools.record import (
    record_meal,
    confirm_record,
    reject_record,
    get_pending_records,
    get_daily_intake,
    get_day_total,
    get_weekly_trend,
    get_weekly_summary,
)


def setup_tmp_db():
    tmp_db = os.path.join(tempfile.gettempdir(), "test_b_record.db")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    real_db = SQLiteDatabase(tmp_db)
    real_db.init_db()
    import db.db as db_module
    db_module._db_instance = real_db
    with open(_ROOT / "backend" / "data" / "dishes.csv", encoding="utf-8") as f:
        real_db.bulk_insert_dishes(list(csv.DictReader(f)))
    # reload tools.record so its module-level `db = get_db()` picks up the temp instance
    import importlib
    import tools.record as record_mod
    importlib.reload(record_mod)
    return tmp_db


def test_record_and_confirm():
    rid = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch", "dish_id": 1})
    assert isinstance(rid, int) and rid > 0
    assert confirm_record.invoke({"record_id": rid}) is True
    print(f"  record+confirm: id={rid} OK")


def test_record_and_reject():
    rid = record_meal.invoke({"date": "2026-08-03", "meal_time": "dinner", "dish_id": 2})
    assert reject_record.invoke({"record_id": rid}) is True
    # rejected records should not appear in confirmed aggregates
    assert get_pending_records.invoke({}) == [], "rejected should not be pending"
    print(f"  record+reject: id={rid} OK")


def test_pending_records():
    rid = record_meal.invoke({"date": "2026-08-04", "meal_time": "lunch", "dish_id": 3})
    pending = get_pending_records.invoke({})
    assert any(r["id"] == rid for r in pending), "pending should contain the new record"
    print(f"  pending records: {len(pending)} OK")


def test_get_daily_intake():
    rid = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch", "dish_id": 1})
    confirm_record.invoke({"record_id": rid})
    r = get_daily_intake.invoke({"date": "2026-08-03"})
    assert isinstance(r, list) and len(r) > 0
    assert all("meal_time" in d and "total_calories" in d for d in r)
    print(f"  daily intake: {len(r)} meal(s) OK")


def test_get_day_total():
    rid = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch", "dish_id": 1})
    confirm_record.invoke({"record_id": rid})
    r = get_day_total.invoke({"date": "2026-08-03"})
    assert r is not None and "total_calories" in r
    print(f"  day total: {r['total_calories']} kcal OK")


def test_get_weekly_trend():
    trend = get_weekly_trend.invoke({"end_date": "2026-08-09", "days": 7})
    assert len(trend) == 7, "should return 7 days"
    assert all("date" in d and "total_calories" in d for d in trend)
    print(f"  weekly trend: {len(trend)} days OK")


def test_get_weekly_summary():
    r = get_weekly_summary.invoke({"start_date": "2026-08-01", "end_date": "2026-08-07"})
    assert r is not None and "total_calories" in r
    print(f"  weekly summary: {r.get('total_calories')} kcal OK")


if __name__ == "__main__":
    tmp_db = setup_tmp_db()
    try:
        tests = [
            test_record_and_confirm,
            test_record_and_reject,
            test_pending_records,
            test_get_daily_intake,
            test_get_day_total,
            test_get_weekly_trend,
            test_get_weekly_summary,
        ]
        passed = 0
        for t in tests:
            try:
                t()
                passed += 1
                print(f"  PASS: {t.__name__}")
            except Exception as e:
                print(f"  FAIL: {t.__name__} - {e}")
        print(f"\n{passed}/{len(tests)} tests passed")
    finally:
        if os.path.exists(tmp_db):
            try:
                os.remove(tmp_db)
            except Exception:
                pass