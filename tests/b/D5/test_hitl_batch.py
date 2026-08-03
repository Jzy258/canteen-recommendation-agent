import os
import sys
import tempfile
import importlib
from pathlib import Path

_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_ROOT / "backend"))

import csv
from db import SQLiteDatabase


def _setup_tmp_db():
    tmp = os.path.join(tempfile.gettempdir(), "test_hitl_batch.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    real_db = SQLiteDatabase(tmp)
    real_db.init_db()
    import db.db as db_module
    db_module._db_instance = real_db
    with open(_ROOT / "backend" / "data" / "dishes.csv", encoding="utf-8") as f:
        real_db.bulk_insert_dishes(list(csv.DictReader(f)))
    import tools.record as record_mod
    importlib.reload(record_mod)
    return tmp


def _tools():
    import tools.record as record_mod
    return record_mod


def test_pending_by_date():
    t = _tools()
    r1 = t.record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch", "dish_id": 1})
    r2 = t.record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch", "dish_id": 2})
    r3 = t.record_meal.invoke({"date": "2026-08-04", "meal_time": "dinner", "dish_id": 3})
    pend = t.get_pending_records_by_date.invoke({"date": "2026-08-03"})
    ids = {p["id"] for p in pend}
    assert r1 in ids and r2 in ids, "should include both 8-03 records"
    assert r3 not in ids, "should exclude 8-04 record"
    print(f"  pending by date 8-03: {sorted(ids)}")


def test_get_pending_record():
    t = _tools()
    rid = t.record_meal.invoke({"date": "2026-08-05", "meal_time": "lunch", "dish_id": 4})
    rec = t.get_pending_record.invoke({"record_id": rid})
    assert rec is not None and rec["id"] == rid
    assert rec["confirmed"] == 0, "should be pending"
    print(f"  single pending record: id={rid}")


def test_batch_confirm():
    t = _tools()
    r1 = t.record_meal.invoke({"date": "2026-08-06", "meal_time": "lunch", "dish_id": 1})
    r2 = t.record_meal.invoke({"date": "2026-08-06", "meal_time": "lunch", "dish_id": 2})
    r3 = t.record_meal.invoke({"date": "2026-08-06", "meal_time": "lunch", "dish_id": 3})
    n = t.confirm_records.invoke({"record_ids": [r1, r2, r3]})
    assert n == 3, f"should confirm 3, got {n}"
    # confirm again should be 0
    assert t.confirm_records.invoke({"record_ids": [r1, r2, r3]}) == 0
    print(f"  batch confirm: {n} records")


def test_batch_reject():
    t = _tools()
    r1 = t.record_meal.invoke({"date": "2026-08-07", "meal_time": "lunch", "dish_id": 1})
    r2 = t.record_meal.invoke({"date": "2026-08-07", "meal_time": "lunch", "dish_id": 2})
    n = t.reject_records.invoke({"record_ids": [r1, r2]})
    assert n == 2, f"should reject 2, got {n}"
    # rejected records should not be pending
    pend = t.get_pending_records.invoke({})
    ids = {p["id"] for p in pend}
    assert r1 not in ids and r2 not in ids
    print(f"  batch reject: {n} records, not pending")


def test_full_hitl_flow():
    t = _tools()
    rid = t.record_meal.invoke({"date": "2026-08-03", "meal_time": "dinner", "dish_id": 1})
    # pending -> confirm single
    assert t.confirm_record.invoke({"record_id": rid}) is True
    # confirmed record appears in daily intake
    daily = t.get_daily_intake.invoke({"date": "2026-08-03"})
    assert len(daily) >= 1
    print("  full HITL flow OK")


if __name__ == "__main__":
    tmp = _setup_tmp_db()
    try:
        tests = [
            test_pending_by_date,
            test_get_pending_record,
            test_batch_confirm,
            test_batch_reject,
            test_full_hitl_flow,
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
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass