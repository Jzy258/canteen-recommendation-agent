"""
A · D4 评分公式验证测试
覆盖：budget_score / nutrition_score / preference_score / score_dish / score_dishes / recommend
"""
import csv, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "tools"))

from scoring import (
    WEIGHTS, CATEGORY_TARGETS, GOAL_NUTRITION_WEIGHTS,
    budget_score, nutrition_score, preference_score,
    score_dish, score_dishes, recommend,
)

# 加载菜品
dishes = {}
dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
with open(dish_path, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        dishes[r["name"]] = r

# recommend 工具内部通过 get_db() 访问数据库，将其单例指向临时库以隔离测试
tmp_db = os.path.join(tempfile.gettempdir(), "test_d4_scoring.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
from db import SQLiteDatabase
_db_test = SQLiteDatabase(tmp_db)
_db_test.init_db()
with open(dish_path, encoding="utf-8") as f:
    _db_test.bulk_insert_dishes(list(csv.DictReader(f)))
import db as _db_module
_db_module._db_instance = _db_test

try:

    print("=" * 50)
    print("1. 系数配置检查")
    print("=" * 50)
    assert abs(WEIGHTS["budget"] + WEIGHTS["nutrition"] + WEIGHTS["preference"] - 1.0) < 1e-6, "权重之和应为1"
    assert set(CATEGORY_TARGETS.keys()) == {"荤菜", "素菜", "汤", "主食", "水果", "饮品"}, "分类目标缺失"
    assert set(GOAL_NUTRITION_WEIGHTS.keys()) >= {"", "高蛋白", "控油", "控糖", "减脂"}
    print(f"  [PASS] 权重: budget={WEIGHTS['budget']} nutrition={WEIGHTS['nutrition']} preference={WEIGHTS['preference']}")
    print(f"  [PASS] 分类目标 {len(CATEGORY_TARGETS)} 类, 营养目标 {len(GOAL_NUTRITION_WEIGHTS)} 档")

    # ============================================================
    print("\n" + "=" * 50)
    print("2. 预算约束 budget_score")
    print("=" * 50)
    assert budget_score(5, 10) == 1.0
    assert budget_score(10, 10) == 1.0
    assert budget_score(12, 10) == 0.9
    assert budget_score(30, 10) == 0.0
    assert budget_score(12, 0) == 1.0  # 无约束
    print("  [PASS] 预算内=1, 超预算线性衰减, 无预算=1")

    # ============================================================
    print("\n" + "=" * 50)
    print("3. 营养均衡 nutrition_score")
    print("=" * 50)
    # 控油目标：红烧肉(高脂) 应低于 清炒小白菜(低脂)
    s_meat = nutrition_score(dishes["红烧肉"], "控油")
    s_veg = nutrition_score(dishes["清炒小白菜"], "控油")
    assert s_veg > s_meat, f"控油目标下素菜应得分更高: veg={s_veg} meat={s_meat}"
    print(f"  [PASS] 控油: 素菜{s_veg} > 荤菜{s_meat}")

    # 无目标时红烧肉得分应高于控油时
    s_meat_generic = nutrition_score(dishes["红烧肉"])
    assert s_meat_generic > s_meat, "无目标应高于控油目标得分"
    print(f"  [PASS] 无目标 {s_meat_generic} > 控油 {s_meat}")

    # 完美匹配目标时得分接近1
    perfect = {"name": "x", "category": "荤菜", "calories": 350, "protein": 22,
               "carbs": 15, "fat": 20}
    assert nutrition_score(perfect) > 0.95, "完美匹配应接近1"
    print("  [PASS] 完美匹配类别目标得分接近1")

    # ============================================================
    print("\n" + "=" * 50)
    print("4. 偏好 preference_score")
    print("=" * 50)
    pref = {"flavor_preferences": "清淡", "health_goals": ""}
    assert abs(preference_score(dishes["清炒小白菜"], pref) - 0.8) < 1e-6
    assert preference_score(dishes["红烧肉"], pref) < 0.8
    print("  [PASS] 口味匹配: 清淡偏好下小白菜=0.8(口味1.0+类别中性0.2)")

    # 无偏好中性0.5 + 类别0.5 = 0.5
    neutral = {"flavor_preferences": "", "health_goals": ""}
    assert abs(preference_score(dishes["红烧肉"], neutral) - 0.5) < 1e-6
    print("  [PASS] 无偏好中性0.5")

    # 控油偏好素菜
    lean = {"flavor_preferences": "", "health_goals": "控油"}
    s_veg_lean = preference_score(dishes["清炒小白菜"], lean)
    s_meat_lean = preference_score(dishes["红烧肉"], lean)
    assert s_veg_lean > s_meat_lean
    print(f"  [PASS] 控油偏好: 素菜{s_veg_lean} > 荤菜{s_meat_lean}")

    # ============================================================
    print("\n" + "=" * 50)
    print("5. 综合评分 score_dish")
    print("=" * 50)
    profile = {"budget": 15, "flavor_preferences": "清淡", "health_goals": "控油"}
    s = score_dish(dishes["清炒小白菜"], profile)
    assert 0 <= s["score"] <= 1
    assert all(k in s for k in ("score", "budget_score", "nutrition_score", "preference_score"))
    print(f"  [PASS] 综合评分结构完整: {s}")

    # 预算约束应体现在总分中：超预算菜品总分降低
    cheap_profile = {"budget": 10, "flavor_preferences": "", "health_goals": ""}
    rich_profile = {"budget": 50, "flavor_preferences": "", "health_goals": ""}
    s_cheap = score_dish(dishes["红烧肉"], cheap_profile)
    s_rich = score_dish(dishes["红烧肉"], rich_profile)
    assert s_cheap["score"] < s_rich["score"], "预算越低得分应越低"
    print(f"  [PASS] 预算约束生效: 预算10={s_cheap['score']} < 预算50={s_rich['score']}")

    # ============================================================
    print("\n" + "=" * 50)
    print("6. 批量排序 score_dishes")
    print("=" * 50)
    all_dishes = list(dishes.values())
    ranked = score_dishes(all_dishes, {"budget": 10, "flavor_preferences": "清淡",
                                        "health_goals": ""}, budget=10)
    assert ranked[0]["score"] >= ranked[-1]["score"], "应按分数降序"
    assert len(ranked) == len(all_dishes)
    print(f"  [PASS] 共{len(ranked)}道按分数降序排列")
    print(f"  [PASS] Top3: {[d['name'] for d in ranked[:3]]}")

    # ============================================================
    print("\n" + "=" * 50)
    print("7. recommend @tool")
    print("=" * 50)
    result = recommend.invoke({"budget": 10, "preferences": "清淡",
                               "health_goals": "", "top_k": 5})
    assert len(result) == 5
    assert all("score" in d and "name" in d for d in result)
    # 预算内推荐
    assert all(d["price"] <= 10 for d in result)
    print(f"  [PASS] recommend 返回5道, 全部在预算内: {[d['name'] for d in result]}")

    # 默认参数
    result2 = recommend.invoke({})
    assert len(result2) == 5
    print("  [PASS] recommend 默认参数(budget=20)可用")

    # ============================================================
    print("\n" + "=" * 50)
    print("8. recommend 合并已存画像")
    print("=" * 50)
    # 先设置已存画像：清淡偏好
    _db_test.upsert_user_profile(budget=15, flavor_preferences="清淡")
    # 不传 preferences/health_goals，应回落到已存画像的"清淡"
    r_default = recommend.invoke({"budget": 15})
    top_default = [d["name"] for d in r_default[:5]]
    # 传显式 preferences 应覆盖已存画像
    r_explicit = recommend.invoke({"budget": 15, "preferences": "辣"})
    top_explicit = [d["name"] for d in r_explicit[:5]]
    # 清淡偏好的推荐应与辣偏好不同（至少一个差异）
    assert top_default != top_explicit, "显式偏好应覆盖已存画像导致推荐变化"
    print(f"  [PASS] 清淡画像推荐: {top_default[:3]}")
    print(f"  [PASS] 显式辣偏好推荐: {top_explicit[:3]}")
    print("  [PASS] recommend 已存画像回落 + 显式参数覆盖")

    print("\n" + "=" * 50)
    print("全部验证通过")
    print("=" * 50)

finally:
    if os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass