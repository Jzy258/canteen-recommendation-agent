"""
A · D4–D5 交付物验收验证
逐项核验：scoring.py / optimizer.py / 评分公式说明.md / db.py HITL 接口 / 联调
"""
import csv, json, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "tools"))

passes = 0
fails = 0

def check(name, cond, detail=""):
    global passes, fails
    if cond:
        passes += 1
        print(f"  [PASS] {name}")
    else:
        fails += 1
        print(f"  [FAIL] {name} {detail}")

print("=" * 55)
print("交付物 1: backend/tools/scoring.py")
print("=" * 55)
scoring_path = os.path.join(_PROJECT_ROOT, "backend", "tools", "scoring.py")
content = open(scoring_path, encoding="utf-8").read()
check("包含评分公式 score_dish", "def score_dish" in content)
check("包含批量评分 score_dishes", "def score_dishes" in content)
check("包含 recommend @tool", "def recommend" in content and "@tool" in content)
check("包含 WEIGHTS 系数", "WEIGHTS" in content and "0.35" in content and "0.40" in content)
check("包含 6 类营养目标", "CATEGORY_TARGETS" in content and "主食" in content)
check("包含 6 档健康目标权重", "GOAL_NUTRITION_WEIGHTS" in content and "控油" in content)

from scoring import (
    WEIGHTS, CATEGORY_TARGETS, GOAL_NUTRITION_WEIGHTS,
    score_dish, score_dishes, recommend, budget_score, nutrition_score,
)
check("权重之和为1", abs(sum(WEIGHTS.values()) - 1.0) < 1e-6)
check("营养目标覆盖全部类别", set(CATEGORY_TARGETS.keys()) == {"荤菜","素菜","汤","主食","水果","饮品"})

print("\n" + "=" * 55)
print("交付物 2: backend/tools/optimizer.py")
print("=" * 55)
opt_path = os.path.join(_PROJECT_ROOT, "backend", "tools", "optimizer.py")
opt_content = open(opt_path, encoding="utf-8").read()
check("包含 optimize_meal 背包DP", "def optimize_meal" in opt_content and "dp" in opt_content)
check("包含荤素搭配修正", "def _ensure_balance" in opt_content)
check("包含 optimize_meal_tool @tool", "optimize_meal_tool" in opt_content and "@tool" in opt_content)

from optimizer import optimize_meal, optimize_meal_tool
check("常量 REQUIRED_CATEGORIES", "REQUIRED_CATEGORIES" in opt_content)

print("\n" + "=" * 55)
print("交付物 3: docs/评分公式说明.md")
print("=" * 55)
doc_path = os.path.join(_PROJECT_ROOT, "docs", "评分公式说明.md")
doc = open(doc_path, encoding="utf-8").read()
for kw in ["评分公式", "预算约束", "营养均衡", "偏好权重", "系数", "调整策略",
           "组合优化", "验证结果"]:
    check(f"文档含 '{kw}'", kw in doc)
check("文档版本标注", "v1.2" in doc)

print("\n" + "=" * 55)
print("交付物 4: db.py HITL 接口函数")
print("=" * 55)
db_path = os.path.join(_PROJECT_ROOT, "backend", "db", "db.py")
db_code = open(db_path, encoding="utf-8").read()
for m in ["add_meal_record", "confirm_meal_record", "reject_meal_record",
          "get_pending_records", "get_pending_records_by_date",
          "get_pending_record", "confirm_records", "reject_records",
          "upsert_user_profile", "update_nutrition_summary",
          "_refresh_profile_summary"]:
    check(f"db.py 含 {m}", f"def {m}" in db_code)
check("确认后刷新营养汇总", "confirmed = 1" in db_code and "_refresh_profile_summary" in db_code)

from db import DatabaseInterface, SQLiteDatabase
impl = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
abstr = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
check("接口抽象与实现一致", abstr.issubset(impl))

print("\n" + "=" * 55)
print("交付物 5: 联调通过（HITL 审批流）")
print("=" * 55)

tmp_db = os.path.join(tempfile.gettempdir(), "test_d45_accept.db")
db = SQLiteDatabase(tmp_db)
db.init_db()
dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
with open(dish_path, encoding="utf-8") as f:
    db.bulk_insert_dishes(list(csv.DictReader(f)))
db.upsert_user_profile(budget=20, flavor_preferences="清淡")

# 评分联调
scored = score_dishes(db.get_all_dishes(), {"budget": 10, "flavor_preferences": "清淡", "health_goals": ""}, budget=10)
check("评分排序正确", scored[0]["score"] >= scored[-1]["score"])
rec = recommend.invoke({"budget": 10, "top_k": 3})
check("recommend @tool 返回", len(rec) == 3 and all("score" in d for d in rec))

# 组合优化联调
opt = optimize_meal(db.get_all_dishes(), 20, 800)
check("优化搭配荤素合理", opt["balance_ok"] and opt["categories"].get("荤菜",0) >= 1 and opt["categories"].get("素菜",0) >= 1)
opt_tool = optimize_meal_tool.invoke({"budget": 20, "calorie_limit": 800})
check("optimize_meal_tool 可调用", opt_tool["balance_ok"])

# HITL 审批流联调
rid1 = db.add_meal_record("2026-08-03", "lunch", 1, 1.0)
rid2 = db.add_meal_record("2026-08-03", "lunch", 16, 1.0)
rid3 = db.add_meal_record("2026-08-03", "dinner", 3, 1.0)
check("待确认3条", len(db.get_pending_records()) == 3)
check("确认1", db.confirm_meal_record(rid1))
check("拒绝2", db.reject_meal_record(rid2))
check("确认后营养聚合", abs(db.get_day_total("2026-08-03")["total_calories"] - 500.0) < 1e-6)
profile = db.get_user_profile()
summary = json.loads(profile["nutrition_summary"])
check("user_profile 营养汇总刷新", summary.get("record_count") == 1)
check("汇总含趋势", "recent_trend" in summary)

os.remove(tmp_db)

print("\n" + "=" * 55)
print(f"交付物验收: {passes} 通过, {fails} 失败")
print("=" * 55)
if fails == 0:
    print("D4–D5 交付物全部验收通过")
else:
    print("存在失败项")
sys.exit(1 if fails else 0)