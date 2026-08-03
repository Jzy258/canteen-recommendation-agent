"""A · D5 边界场景验证（供 C 测试的数据正确性自检）
覆盖：评分边界 / 摄入边界 / 场景不崩溃，对应 edge_*.csv 与 README 断言。"""
import csv, json, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "tools"))

from db import SQLiteDatabase
from scoring import budget_score, preference_score, nutrition_score
from optimizer import optimize_meal

ok = 0

def check(name, cond):
    global ok
    assert cond, f"FAIL: {name}"
    ok += 1
    print(f"  [PASS] {name}")

print("=== 评分边界 ===")
check("超预算 S_budget=0.9", abs(budget_score(12, 10) - 0.9) < 1e-6)
check("双倍超预算 S_budget=0.75", abs(budget_score(15, 10) - 0.75) < 1e-6)
check("无预算 S_budget=1.0", budget_score(12, 0) == 1.0)
check("无偏好 0.5", abs(preference_score({"category": "荤菜", "flavor_tags": "咸"},
                                        {"flavor_preferences": "", "health_goals": ""}) - 0.5) < 1e-6)
check("控油偏好素菜 0.7", abs(preference_score({"category": "素菜", "flavor_tags": "清淡"},
                                             {"flavor_preferences": "", "health_goals": "控油"}) - 0.7) < 1e-6)
check("减脂偏好荤菜 0.42", abs(preference_score({"category": "荤菜", "flavor_tags": "咸"},
                                             {"flavor_preferences": "", "health_goals": "减脂"}) - 0.42) < 1e-6)
perfect = {"category": "荤菜", "calories": 350, "protein": 22, "carbs": 15, "fat": 20}
check("完美营养 ≈1.0", nutrition_score(perfect) > 0.95)

print("\n=== 摄入边界（临时库） ===")
tmp_db = os.path.join(tempfile.gettempdir(), "test_edge.db")
db = SQLiteDatabase(tmp_db)
db.init_db()
dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
with open(dish_path, encoding="utf-8") as f:
    db.bulk_insert_dishes(list(csv.DictReader(f)))

with open(os.path.join(_PROJECT_ROOT, "tests", "A", "D5", "edge_meal_records.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    rid = db.add_meal_record(r["date"], r["meal_time"], int(r["dish_id"]), float(r["portion"]))
    if r["confirmed"] == "1":
        db.confirm_meal_record(rid)

check("8-10 全天 = 450kcal", abs(db.get_day_total("2026-08-10")["total_calories"] - 450.0) < 1e-6)
check("待确认 2 条", len(db.get_pending_records()) == 2)
trend = db.get_weekly_trend(end_date="2026-08-13", days=7)
dmap = {t["date"]: t["total_calories"] for t in trend}
check("8-12 补零", dmap["2026-08-12"] == 0)
check("8-10 计入确认", abs(dmap["2026-08-10"] - 450.0) < 1e-6)
check("8-13 鱼香肉丝 280", abs(dmap["2026-08-13"] - 280.0) < 1e-6)

print("\n=== 边界场景（不崩溃） ===")
dishes = db.get_all_dishes()
r1 = optimize_meal(dishes, 20, 300)
print(f"  超热量上限 balance_ok={r1['balance_ok']} reason={r1['reason']} (不崩溃即可)")
check("超热量上限不崩溃", isinstance(r1, dict))
r2 = optimize_meal(dishes, 20, 0)
check("热量上限0返回空", r2["dishes"] == [] and r2["reason"])
r3 = optimize_meal(dishes, 0, 800)
check("预算0返回空", r3["dishes"] == [])
check("无匹配菜品返回空", db.search_dishes(keyword="佛跳墙") == [])
check("max_price=1 有结果", len(db.search_dishes(max_price=1)) > 0)

os.remove(tmp_db)
print(f"\n全部 {ok} 项边界断言通过")