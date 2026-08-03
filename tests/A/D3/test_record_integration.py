"""
A · D3 联调验证：模拟 B 的 tools/record.py 调用聚合函数

背景：B 的 search.py 采用 `from db import get_db` + `@tool` 模式，
本测试用相同模式模拟 record.py，验证 A 提供的聚合接口可被正确调用。

记录 B 确认的调用契约。
"""
import csv, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))

tmp_db = None

# ============================================================
# 模拟 B 的 tools/record.py（与 search.py 同款模式）
# ============================================================
from langchain_core.tools import tool
from db import get_db

db = get_db()


@tool
def record_meal(date: str, meal_time: str, dish_id: int, portion: float = 1.0) -> int:
    """Record a meal intake (pending confirmation)."""
    return db.add_meal_record(date, meal_time, dish_id, portion)


@tool
def confirm_record(record_id: int) -> bool:
    """Confirm a pending meal record."""
    return db.confirm_meal_record(record_id)


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
    """Get daily nutrition totals for the last N days."""
    return db.get_weekly_trend(end_date=end_date, days=days)


@tool
def get_week_summary(start: str, end: str) -> dict:
    """Get weekly nutrition summary."""
    return db.get_weekly_summary(start, end)


try:
    print("=" * 50)
    print("A·B 联调：record.py 模拟验证")
    print("=" * 50)

    # 使用独立临时数据库，避免污染 canteen.db
    tmp_db = os.path.join(tempfile.gettempdir(), "test_record_join.db")
    from db import SQLiteDatabase
    real_db = SQLiteDatabase(tmp_db)
    real_db.init_db()

    # 将模块级 db 变量重绑定到临时库（工具引用的是该变量），并同步单例
    db = real_db
    import db as db_module
    db_module._db_instance = real_db

    with open(os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv"), encoding="utf-8") as f:
        dishes = list(csv.DictReader(f))
    real_db.bulk_insert_dishes(dishes)

    # ---- 1. record_meal 新增记录 ----
    print("\n1. record_meal 新增待确认记录")
    rid1 = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch",
                               "dish_id": 1, "portion": 1.0})
    rid2 = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch",
                               "dish_id": 16, "portion": 1.0})
    rid3 = record_meal.invoke({"date": "2026-08-03", "meal_time": "dinner",
                               "dish_id": 3, "portion": 1.0})
    rid4 = record_meal.invoke({"date": "2026-08-04", "meal_time": "lunch",
                               "dish_id": 2, "portion": 1.0})
    assert rid1 > 0 and rid2 > 0 and rid3 > 0 and rid4 > 0
    print("  [PASS] 4 条记录创建成功, ids:", [rid1, rid2, rid3, rid4])

    # ---- 2. 未确认时聚合应为空 ----
    print("\n2. 未确认时聚合为空")
    assert db.get_daily_nutrition("2026-08-03") == []
    assert db.get_weekly_trend(end_date="2026-08-09", days=7)[0]["total_calories"] == 0
    print("  [PASS] 未确认记录不计入聚合")

    # ---- 3. confirm_record 确认 ----
    print("\n3. confirm_record 确认")
    for rid in [rid1, rid2, rid3, rid4]:
        assert confirm_record.invoke({"record_id": rid}) is True
    print("  [PASS] 4 条记录确认成功")

    # ---- 4. get_daily_intake 按餐次 ----
    print("\n4. get_daily_intake 按餐次")
    daily = get_daily_intake.invoke({"date": "2026-08-03"})
    assert len(daily) == 2, f"应2餐次: {daily}"
    lunch = {r["meal_time"]: r for r in daily}["lunch"]
    assert lunch["total_calories"] == 580.0, f"lunch 红烧肉500+小白菜80=580: {lunch}"
    print("  [PASS] 8-03 lunch = 580kcal (红烧肉500+小白菜80)")

    # ---- 5. get_day_total 全天 ----
    print("\n5. get_day_total 全天")
    dt = get_day_total.invoke({"date": "2026-08-03"})
    assert dt["total_calories"] == 860.0, f"全天 580+280=860: {dt}"
    assert dt["total_protein"] == 41.0
    assert dt["dish_count"] == 3
    print("  [PASS] 8-03 全天 = 860/41/..., 3菜")

    # ---- 6. get_weekly_trend 趋势 ----
    print("\n6. get_weekly_trend 趋势")
    trend = get_weekly_trend.invoke({"end_date": "2026-08-09", "days": 7})
    assert len(trend) == 7
    assert trend[0]["total_calories"] == 860.0
    assert trend[1]["total_calories"] == 350.0  # 8-04 宫保鸡丁
    assert trend[2]["total_calories"] == 0       # 8-05 补零
    print("  [PASS] 趋势正确, 缺日期补零")

    # ---- 7. get_week_summary 周汇总 ----
    print("\n7. get_week_summary 周汇总")
    summary = get_week_summary.invoke({"start": "2026-08-01", "end": "2026-08-07"})
    assert summary["total_calories"] == 1210.0, f"860+350=1210: {summary}"
    assert summary["day_count"] == 2
    print("  [PASS] 周汇总 = 1210kcal, 2天")

    # ---- 8. 链式：确认流程完整性 ----
    print("\n8. 完整流程: 记录→确认→聚合")
    rid5 = record_meal.invoke({"date": "2026-08-05", "meal_time": "lunch",
                               "dish_id": 6, "portion": 1.0})
    assert confirm_record.invoke({"record_id": rid5}) is True
    trend2 = get_weekly_trend.invoke({"end_date": "2026-08-09", "days": 7})
    assert trend2[2]["total_calories"] == 380.0
    print("  [PASS] 新增确认后趋势即时更新")

    print("\n" + "=" * 50)
    print("联调验证全部通过")
    print("=" * 50)

finally:
    if tmp_db and os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass