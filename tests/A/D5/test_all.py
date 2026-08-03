"""
A · D5 HITL 审批数据接口验证
覆盖：待确认缓存 / 确认写入 / 拒绝丢弃 / 批量审批 / 营养汇总刷新
"""
import csv, json, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))

tmp_db = None
conn = None

try:

    print("=" * 50)
    print("1. HITL 接口完整性检查")
    print("=" * 50)

    schema_path = os.path.join(_PROJECT_ROOT, "backend", "db", "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()
    assert "confirmed" in schema, "meal_record 缺 confirmed 字段"
    assert "0=待确认" in schema, "schema 未注释 HITL 状态含义"
    print("  [PASS] schema 含 confirmed 状态字段(0待确认/1确认/-1拒绝)")

    from db import DatabaseInterface, SQLiteDatabase
    interface_methods = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
    impl_methods = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
    for m in ["add_meal_record", "confirm_meal_record", "reject_meal_record",
              "get_pending_records", "get_pending_records_by_date",
              "get_pending_record", "confirm_records", "reject_records"]:
        assert m in interface_methods, f"抽象接口缺少 {m}"
        assert m in impl_methods, f"实现缺少 {m}"
    print(f"  [PASS] 8 个 HITL 接口均已声明并实现")

    # ============================================================
    print("\n" + "=" * 50)
    print("2. 临时库准备")
    print("=" * 50)

    tmp_db = os.path.join(tempfile.gettempdir(), "test_d5_hitl.db")
    db = SQLiteDatabase(tmp_db)
    db.init_db()

    dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
    with open(dish_path, encoding="utf-8") as f:
        dishes = list(csv.DictReader(f))
    db.bulk_insert_dishes(dishes)

    # 创建用户画像（budget 等）
    db.upsert_user_profile(budget=20, flavor_preferences="清淡")
    print("  [PASS] 菜品库 + 用户画像就绪")

    # ============================================================
    print("\n" + "=" * 50)
    print("3. 新增待确认记录")
    print("=" * 50)
    ids = []
    for date, meal, did in [
        ("2026-08-03", "lunch", 1), ("2026-08-03", "lunch", 16),
        ("2026-08-03", "dinner", 3), ("2026-08-04", "lunch", 2),
    ]:
        ids.append(db.add_meal_record(date, meal, did, 1.0))
    assert all(i > 0 for i in ids)
    print(f"  [PASS] 新增 4 条待确认记录: {ids}")

    # ============================================================
    print("\n" + "=" * 50)
    print("4. 待确认记录缓存")
    print("=" * 50)
    pending = db.get_pending_records()
    assert len(pending) == 4, f"应有4条待确认: {len(pending)}"
    assert all(p["confirmed"] == 0 for p in pending)
    assert all("dish_name" in p and "calories" in p for p in pending)
    print(f"  [PASS] get_pending_records 返回 {len(pending)} 条（含菜品名+营养）")

    by_date = db.get_pending_records_by_date("2026-08-03")
    assert len(by_date) == 3, f"8-03 应有3条: {len(by_date)}"
    by_date_meal = db.get_pending_records_by_date("2026-08-03", "lunch")
    assert len(by_date_meal) == 2, f"8-03 lunch 应有2条: {len(by_date_meal)}"
    print("  [PASS] get_pending_records_by_date 支持日期/日期+餐次过滤")

    one = db.get_pending_record(ids[0])
    assert one is not None and one["id"] == ids[0]
    assert db.get_pending_record(9999) is None
    print("  [PASS] get_pending_record 单条查询 + 不存在返回 None")

    # ============================================================
    print("\n" + "=" * 50)
    print("5. 确认写入")
    print("=" * 50)
    assert db.confirm_meal_record(ids[0]) is True
    assert db.confirm_meal_record(ids[0]) is False  # 已确认，再确认应 False
    records = db.get_records_by_date("2026-08-03")
    assert len(records) == 1 and records[0]["confirmed"] == 1
    assert len(db.get_pending_records()) == 3
    print("  [PASS] 单条确认 + 幂等（重复确认返回 False）")

    # 确认后营养汇总应已刷新
    profile = db.get_user_profile()
    assert profile is not None
    summary = json.loads(profile["nutrition_summary"])
    assert summary.get("record_count") == 1, f"营养汇总应含1条记录: {summary}"
    assert summary.get("day_count") == 1
    assert abs(summary["avg_calories"] - 500.0) < 1e-6  # 红烧肉500
    assert summary.get("dish_kind_count") == 1
    assert summary.get("total_calories") == 500.0
    assert "meal_averages" in summary and summary["meal_averages"].get("lunch") == 500.0
    assert "recent_trend" in summary and summary["recent_trend"][-1]["calories"] == 500.0
    print(f"  [PASS] 确认后 user_profile 营养汇总刷新: {summary}")

    # ============================================================
    print("\n" + "=" * 50)
    print("6. 拒绝丢弃")
    print("=" * 50)
    assert db.reject_meal_record(ids[1]) is True
    assert db.reject_meal_record(ids[1]) is False  # 已拒绝，再拒绝应 False
    rejected = db.get_pending_records()
    assert all(r["confirmed"] == 0 for r in rejected)
    assert len(rejected) == 2  # 4 - 1确认 - 1拒绝
    # 被拒绝的记录不进入已确认列表
    assert len(db.get_records_by_date("2026-08-03")) == 1
    print("  [PASS] 拒绝丢弃 + 幂等 + 不进入已确认")

    # ============================================================
    print("\n" + "=" * 50)
    print("7. 批量确认/拒绝")
    print("=" * 50)
    # ids[2] 确认, ids[3] 拒绝
    assert db.confirm_records([ids[2]]) == 1
    assert db.reject_records([ids[3]]) == 1
    assert db.confirm_records([ids[2]]) == 0  # 已确认，批量再确认0条
    assert db.confirm_records([]) == 0
    assert db.reject_records([]) == 0
    assert len(db.get_pending_records()) == 0
    print("  [PASS] 批量确认/拒绝 + 幂等 + 空列表返回0")

    # 全部处理后营养汇总应为2条记录
    profile = db.get_user_profile()
    summary = json.loads(profile["nutrition_summary"])
    assert summary.get("record_count") == 2, f"应2条: {summary}"
    assert summary.get("dish_kind_count") == 2  # 红烧肉 + 鱼香肉丝
    assert "meal_averages" in summary and summary["meal_averages"].get("dinner") == 280.0
    print(f"  [PASS] 最终营养汇总: {summary}")

    # ============================================================
    print("\n" + "=" * 50)
    print("8. 汇总查询（确认后聚合）")
    print("=" * 50)
    daily = db.get_daily_nutrition("2026-08-03")
    assert len(daily) == 2  # 红烧肉(确认) lunch + 鱼香肉丝(确认) dinner
    lunch_total = {r["meal_time"]: r for r in daily}["lunch"]["total_calories"]
    assert lunch_total == 500.0
    print(f"  [PASS] 确认记录正确进入聚合: {daily}")

    # ============================================================
    print("\n" + "=" * 50)
    print("9. 多日营养汇总（meal_averages 按天平均 / recent_trend 多日）")
    print("=" * 50)
    # 新增第二天记录并确认，验证多日统计
    rid5 = db.add_meal_record("2026-08-04", "lunch", 6, 1.0)   # 土豆烧牛肉 380
    rid6 = db.add_meal_record("2026-08-04", "dinner", 12, 1.0) # 西红柿炒鸡蛋 180
    db.confirm_records([rid5, rid6])
    profile = db.get_user_profile()
    summary = json.loads(profile["nutrition_summary"])
    assert summary["record_count"] == 4, f"应4条: {summary}"
    assert summary["day_count"] == 2, f"应2天: {summary}"
    # 日均热量 = (780 + 560) / 2 = 670
    assert abs(summary["avg_calories"] - 670.0) < 1e-6, f"日均应670: {summary}"
    # 餐次平均：lunch = (500+380)/2 = 440
    assert abs(summary["meal_averages"]["lunch"] - 440.0) < 1e-6, summary["meal_averages"]
    assert abs(summary["meal_averages"]["dinner"] - (280 + 180) / 2) < 1e-6
    # 趋势：2天
    assert len(summary["recent_trend"]) == 2
    assert summary["recent_trend"][-1]["calories"] == 560.0
    print(f"  [PASS] 多日汇总: record_count=4, day_count=2, avg=670, "
          f"meal_averages={summary['meal_averages']}, trend={summary['recent_trend']}")

    # ============================================================
    print("\n" + "=" * 50)
    print("10. 部分更新保留旧值（upsert 非空覆盖）")
    print("=" * 50)
    # 初始画像: budget=20, flavor_preferences=清淡, health_goals=减脂
    db.upsert_user_profile(budget=20, flavor_preferences="清淡", health_goals="减脂")
    p0 = db.get_user_profile()
    assert p0["flavor_preferences"] == "清淡" and p0["health_goals"] == "减脂"
    # 只更新 budget，其余字段应保留
    db.upsert_user_profile(budget=30)
    p1 = db.get_user_profile()
    assert p1["budget"] == 30.0, f"预算应更新为30: {p1}"
    assert p1["flavor_preferences"] == "清淡", f"口味应保留: {p1}"
    assert p1["health_goals"] == "减脂", f"健康目标应保留: {p1}"
    # 只更新 health_goals，budget/口味保留
    db.upsert_user_profile(health_goals="控油")
    p2 = db.get_user_profile()
    assert p2["health_goals"] == "控油"
    assert p2["budget"] == 30.0 and p2["flavor_preferences"] == "清淡"
    print(f"  [PASS] 部分更新保留旧值: budget=30, 偏好保留清淡/控油")
    print(f"  [PASS] upsert 覆盖式更新已修复（不再丢字段）")

    print("\n" + "=" * 50)
    print("全部验证通过")
    print("=" * 50)

finally:
    for c in [conn]:
        try:
            c.close()
        except Exception:
            pass
    if tmp_db and os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass