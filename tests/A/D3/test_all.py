"""
A · D3 阶段全部验证测试
覆盖：meal_record 聚合查询（按天/按周：总热量、蛋白质、碳水、脂肪）
"""
import csv, os, sys, tempfile

# 项目根目录（tests/A/D3/test_all.py → 上3层）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))

conn = None
tmp_db = None

try:

    print("=" * 50)
    print("1. 聚合视图检查")
    print("=" * 50)

    schema_path = os.path.join(_PROJECT_ROOT, "backend", "db", "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()

    for view in ["v_daily_nutrition", "v_day_total", "v_weekly_nutrition", "v_week_summary"]:
        assert f"CREATE VIEW IF NOT EXISTS {view}" in schema, f"缺少视图 {view}"
        print(f"  [PASS] 视图 {view}")

    # ============================================================
    # 2. 聚合方法接口完整性
    # ============================================================
    print("\n" + "=" * 50)
    print("2. 聚合方法接口完整性")
    print("=" * 50)

    from db import DatabaseInterface, SQLiteDatabase

    interface_methods = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
    impl_methods = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
    for m in ["get_daily_nutrition", "get_day_total", "get_weekly_nutrition", "get_weekly_summary", "get_weekly_trend"]:
        assert m in interface_methods, f"抽象接口缺少 {m}"
        assert m in impl_methods, f"实现缺少 {m}"
    print("  [PASS] 5 个聚合方法均已声明并实现")

    # ============================================================
    # 3. 聚合正确性验证（临时数据库）
    # ============================================================
    print("\n" + "=" * 50)
    print("3. 聚合正确性验证（临时数据库）")
    print("=" * 50)

    tmp_db = os.path.join(tempfile.gettempdir(), "test_canteen_d3.db")
    db = SQLiteDatabase(tmp_db)
    db.init_db()

    dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
    with open(dish_path, encoding="utf-8") as f:
        dishes = list(csv.DictReader(f))
    db.bulk_insert_dishes(dishes)

    # 预期营养数据
    # 1 红烧肉 500/20/10/35 ; 16 清炒小白菜 80/3/5/4 ; 37 米饭 200/4/45/0.5
    # 3 鱼香肉丝 280/18/20/16 ; 2 宫保鸡丁 350/25/15/22 ; 6 土豆烧牛肉 380/28/20/20
    records = [
        ("2026-08-03", "lunch", 1, 1.0),
        ("2026-08-03", "lunch", 16, 1.0),
        ("2026-08-03", "lunch", 37, 1.0),
        ("2026-08-03", "dinner", 3, 1.0),
        ("2026-08-04", "lunch", 2, 1.0),
        ("2026-08-05", "lunch", 6, 1.0),
        ("2026-08-05", "lunch", 37, 1.0),  # 不确认，应被排除
    ]
    ids = []
    for date, meal, did, portion in records:
        ids.append(db.add_meal_record(date, meal, did, portion))
    for rid in ids[:6]:
        db.confirm_meal_record(rid)

    # 3.1 按天+餐次
    print("  [PASS] 3.1 按天+餐次")
    daily = db.get_daily_nutrition("2026-08-03")
    assert len(daily) == 2, f"8-03 应有2餐次: {daily}"
    lunch = {r["meal_time"]: r for r in daily}["lunch"]
    assert lunch["total_calories"] == 780.0, f"lunch 应780kcal: {lunch}"
    assert lunch["total_protein"] == 27.0
    assert lunch["total_carbs"] == 60.0
    assert lunch["total_fat"] == 39.5
    assert lunch["dish_count"] == 3
    dinner = {r["meal_time"]: r for r in daily}["dinner"]
    assert dinner["total_calories"] == 280.0
    print("  [PASS] 3.1 数值正确 (lunch 780/27/60/39.5, dinner 280/18/20/16)")

    # 3.2 全天合计
    print("  [PASS] 3.2 全天合计")
    day_total = db.get_day_total("2026-08-03")
    assert day_total is not None
    assert day_total["total_calories"] == 1060.0, f"全天应1060: {day_total}"
    assert day_total["total_protein"] == 45.0
    assert day_total["total_carbs"] == 80.0
    assert day_total["total_fat"] == 55.5
    assert day_total["dish_count"] == 4
    print("  [PASS] 3.2 全天合计正确 (1060/45/80/55.5)")

    # 3.3 按天（周范围）
    print("  [PASS] 3.3 按天（周范围）")
    weekly = db.get_weekly_nutrition("2026-08-01", "2026-08-07")
    assert len(weekly) == 3, f"应有3天记录: {weekly}"
    day_map = {r["date"]: r for r in weekly}
    assert day_map["2026-08-03"]["total_calories"] == 1060.0
    assert day_map["2026-08-04"]["total_calories"] == 350.0
    assert day_map["2026-08-05"]["total_calories"] == 380.0  # 未确认的米饭被排除
    print("  [PASS] 3.3 未确认记录被排除 (8-05 仅380kcal)")

    # 3.4 周汇总
    print("  [PASS] 3.4 周汇总")
    summary = db.get_weekly_summary("2026-08-01", "2026-08-07")
    assert summary is not None
    assert summary["total_calories"] == 1790.0, f"周总计应1790: {summary}"
    assert summary["total_protein"] == 98.0
    assert summary["total_carbs"] == 115.0
    assert summary["total_fat"] == 97.5
    assert summary["day_count"] == 3
    assert summary["dish_count"] == 6
    print("  [PASS] 3.4 周汇总正确 (1790/98/115/97.5, 3天6菜)")

    # 3.5 空范围边界
    print("  [PASS] 3.5 空范围边界")
    assert db.get_day_total("2026-09-01") is None
    assert db.get_weekly_summary("2026-09-01", "2026-09-07") is None
    assert db.get_weekly_nutrition("2026-09-01", "2026-09-07") == []
    assert db.get_daily_nutrition("2026-09-01") == []
    print("  [PASS] 3.5 空范围返回 None/[]")

    # 3.6 部分份量验证
    print("  [PASS] 3.6 份量系数")
    rid = db.add_meal_record("2026-08-06", "lunch", 1, 0.5)
    db.confirm_meal_record(rid)
    dt = db.get_day_total("2026-08-06")
    assert dt["total_calories"] == 250.0, f"半份红烧肉应250kcal: {dt}"
    assert dt["total_protein"] == 10.0
    print("  [PASS] 3.6 份量系数正确 (0.5份 → 250kcal)")

    # 3.7 周趋势（缺失补零）
    print("  [PASS] 3.7 周趋势")
    trend = db.get_weekly_trend(end_date="2026-08-09", days=7)
    assert len(trend) == 7, f"应返回7天: {len(trend)}"
    assert trend[0]["date"] == "2026-08-03"
    assert trend[-1]["date"] == "2026-08-09"
    assert trend[0]["total_calories"] == 1060.0  # 8-03 全天
    assert trend[1]["total_calories"] == 350.0    # 8-04
    assert trend[2]["total_calories"] == 380.0    # 8-05 土豆烧牛肉
    assert trend[3]["total_calories"] == 250.0    # 8-06 半份
    assert trend[4]["total_calories"] == 0        # 8-07 补零
    assert trend[6]["total_calories"] == 0        # 8-09 补零
    assert all("total_protein" in r and "total_carbs" in r and "total_fat" in r for r in trend)
    print("  [PASS] 3.7 趋势连续7天，缺失日期补零正确")

    # 3.8 默认参数（今天为终点）
    trend_default = db.get_weekly_trend()
    assert len(trend_default) == 7
    print("  [PASS] 3.8 默认 end_date 返回最近7天")

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