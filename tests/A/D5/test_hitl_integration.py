"""
A · D5 联调验证：B 的 Agent 审批流调用 HITL 接口

背景：B 的 tools/record.py 采用 `from db import get_db` + `@tool` 模式，
agent.py 已注册 record_meal / confirm_record / reject_record / get_pending_records 等。
本测试按同款模式模拟 B 的 Agent 审批流，验证 A 提供的 HITL 接口可被正确调用，
覆盖：记录 → 待确认缓存 → 确认/拒绝 → 营养聚合 + user_profile 汇总刷新。
"""
import csv, json, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))

tmp_db = None

# ============================================================
# 模拟 B 的 tools/record.py（与 agent.py 注册的工具同款）
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
def reject_record(record_id: int) -> bool:
    """Reject a pending meal record."""
    return db.reject_meal_record(record_id)


@tool
def get_pending_records() -> list[dict]:
    """Get all pending meal records (awaiting HITL confirmation)."""
    return db.get_pending_records()


@tool
def get_daily_intake(date: str) -> list[dict]:
    """Get daily nutrition breakdown by meal_time."""
    return db.get_daily_nutrition(date)


@tool
def get_user_nutrition_summary() -> dict:
    """Get user's historical nutrition summary (Store long-term memory)."""
    p = db.get_user_profile()
    return json.loads(p["nutrition_summary"]) if p else {}


try:
    print("=" * 50)
    print("A·B 联调：HITL 审批流验证")
    print("=" * 50)

    # 使用独立临时数据库
    tmp_db = os.path.join(tempfile.gettempdir(), "test_hitl_join.db")
    from db import SQLiteDatabase
    real_db = SQLiteDatabase(tmp_db)
    real_db.init_db()

    # 重绑定模块级 db 变量 + 单例到临时库，隔离测试
    db = real_db
    import db as db_module
    db_module._db_instance = real_db

    with open(os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv"), encoding="utf-8") as f:
        real_db.bulk_insert_dishes(list(csv.DictReader(f)))
    real_db.upsert_user_profile(budget=20, flavor_preferences="清淡")

    # ---- 1. Agent 记录一餐（record_meal） ----
    print("\n1. Agent 记录一餐")
    rid1 = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch",
                               "dish_id": 1, "portion": 1.0})   # 红烧肉
    rid2 = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch",
                               "dish_id": 16, "portion": 1.0})  # 清炒小白菜
    rid3 = record_meal.invoke({"date": "2026-08-03", "meal_time": "dinner",
                               "dish_id": 3, "portion": 1.0})   # 鱼香肉丝
    assert rid1 > 0 and rid2 > 0 and rid3 > 0
    print("  [PASS] 记录 3 道菜, ids:", [rid1, rid2, rid3])

    # ---- 2. 展示待确认（HITL 提示用户） ----
    print("\n2. 待确认记录展示")
    pending = get_pending_records.invoke({})
    assert len(pending) == 3
    names = sorted(p["dish_name"] for p in pending)
    assert "红烧肉" in names and "清炒小白菜" in names and "鱼香肉丝" in names
    assert all(p["confirmed"] == 0 for p in pending)
    print("  [PASS] 3 条待确认（含菜品名+营养）, Agent 可展示给用户确认")

    # ---- 3. 用户确认（confirm_record） ----
    print("\n3. 用户确认午餐")
    assert confirm_record.invoke({"record_id": rid1}) is True
    assert confirm_record.invoke({"record_id": rid2}) is True
    print("  [PASS] 确认 2 条 lunch")

    # ---- 4. 用户拒绝晚餐 ----
    print("\n4. 用户拒绝晚餐")
    assert reject_record.invoke({"record_id": rid3}) is True
    assert len(get_pending_records.invoke({})) == 0
    print("  [PASS] 拒绝 1 条, 无待确认")

    # ---- 5. 确认后营养聚合 ----
    print("\n5. 确认后营养聚合")
    daily = get_daily_intake.invoke({"date": "2026-08-03"})
    lunch = {r["meal_time"]: r for r in daily}["lunch"]
    assert lunch["total_calories"] == 580.0  # 红烧肉500 + 小白菜80
    assert lunch["dish_count"] == 2
    print(f"  [PASS] 8-03 lunch = 580kcal/2菜 (确认的2道，被拒绝的鱼香肉丝不计入)")

    # ---- 6. user_profile 营养汇总刷新（Store 长期记忆） ----
    print("\n6. user_profile 营养汇总（Store 长期记忆）")
    summary = get_user_nutrition_summary.invoke({})
    assert summary["record_count"] == 2, f"应2条: {summary}"
    assert summary["day_count"] == 1
    assert abs(summary["avg_calories"] - 580.0) < 1e-6
    assert summary["dish_kind_count"] == 2
    assert "meal_averages" in summary
    assert "recent_trend" in summary
    print(f"  [PASS] 汇总刷新: {summary}")

    # ---- 7. 全流程串联（Agent 场景） ----
    print("\n7. 全流程串联")
    rid4 = record_meal.invoke({"date": "2026-08-04", "meal_time": "lunch",
                               "dish_id": 6, "portion": 1.0})  # 土豆烧牛肉
    assert confirm_record.invoke({"record_id": rid4}) is True
    s2 = get_user_nutrition_summary.invoke({})
    assert s2["record_count"] == 3
    assert s2["day_count"] == 2
    assert abs(s2["avg_calories"] - (580 + 380) / 2) < 1e-6  # 480
    print(f"  [PASS] 追加一天后: record_count=3, day_count=2, avg={s2['avg_calories']}")

    print("\n" + "=" * 50)
    print("联调验证全部通过")
    print("=" * 50)

finally:
    if tmp_db and os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass