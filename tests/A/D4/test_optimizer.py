"""
A · D4 组合优化算法验证测试
覆盖：optimize_meal 背包DP / 荤素搭配修正 / 约束检查 / @tool
"""
import csv, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "tools"))

from optimizer import optimize_meal, optimize_meal_tool, REQUIRED_CATEGORIES

# 加载菜品
dishes = []
dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
with open(dish_path, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        r["id"] = len(dishes) + 1
        dishes.append(r)

# optimize_meal_tool 内部通过 get_db() 访问数据库，将其单例指向临时库以隔离测试
tmp_db = os.path.join(tempfile.gettempdir(), "test_d4_optimizer.db")
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
    print("1. 正常场景: 预算20 热量上限800")
    print("=" * 50)
    r = optimize_meal(dishes, budget=20, calorie_limit=800)
    assert r["total_price"] <= 20, f"超预算: {r['total_price']}"
    assert r["total_calories"] <= 800, f"超热量: {r['total_calories']}"
    assert r["balance_ok"], f"荤素搭配不OK: {r['reason']}"
    cats = r["categories"]
    for c in REQUIRED_CATEGORIES:
        assert cats.get(c, 0) >= 1, f"缺类别 {c}: {cats}"
    assert r["total_protein"] > 0
    print(f"  [PASS] 预算{r['total_price']}/20, 热量{r['total_calories']}/800, 蛋白质{r['total_protein']}g")
    print(f"  [PASS] 类别分布: {cats}")
    print(f"  [PASS] 荤素搭配: {r['reason']}")

    # ============================================================
    print("\n" + "=" * 50)
    print("2. 高预算大热量可容纳更多菜品")
    print("=" * 50)
    r3 = optimize_meal(dishes, budget=50, calorie_limit=2000)
    assert r3["balance_ok"]
    assert r3["total_price"] <= 50
    assert r3["total_calories"] <= 2000
    assert len(r3["dishes"]) >= 3, f"应至少3道菜: {len(r3['dishes'])}"
    print(f"  [PASS] {len(r3['dishes'])}道菜, 价格{r3['total_price']}, 热量{r3['total_calories']}")
    print(f"  [PASS] 类别分布: {r3['categories']}")

    # ============================================================
    print("\n" + "=" * 50)
    print("3. 约束边界: 预算过低无解")
    print("=" * 50)
    r2 = optimize_meal(dishes, budget=0.5, calorie_limit=800)
    assert not r2["balance_ok"]
    assert r2["dishes"] == []
    assert r2["reason"], "无解时应给出原因"
    print(f"  [PASS] 无解返回空, 原因: {r2['reason']}")

    # ============================================================
    print("\n" + "=" * 50)
    print("4. 热量上限约束")
    print("=" * 50)
    for limit in (300, 500, 1000):
        rr = optimize_meal(dishes, budget=50, calorie_limit=limit)
        assert rr["total_calories"] <= limit, f"超热量上限{limit}"
        print(f"  [PASS] 上限{limit}: 实际{rr['total_calories']}kcal, "
              f"平衡={rr['balance_ok']}")
    print("  [PASS] 全部热量约束满足")

    # ============================================================
    print("\n" + "=" * 50)
    print("5. 非法参数")
    print("=" * 50)
    r_bad = optimize_meal(dishes, budget=0, calorie_limit=800)
    assert r_bad["dishes"] == []
    r_bad2 = optimize_meal(dishes, budget=20, calorie_limit=0)
    assert r_bad2["dishes"] == []
    print("  [PASS] 预算/热量为0时返回空")

    # ============================================================
    print("\n" + "=" * 50)
    print("6. 确定性")
    print("=" * 50)
    a = optimize_meal(dishes, budget=20, calorie_limit=800)
    b = optimize_meal(dishes, budget=20, calorie_limit=800)
    assert [d["id"] for d in a["dishes"]] == [d["id"] for d in b["dishes"]]
    print("  [PASS] 相同输入结果一致")

    # ============================================================
    print("\n" + "=" * 50)
    print("7. @tool optimize_meal_tool")
    print("=" * 50)
    r5 = optimize_meal_tool.invoke({"budget": 20, "calorie_limit": 800})
    assert r5["balance_ok"]
    assert len(r5["dishes"]) >= 3
    print(f"  [PASS] @tool 返回 {len(r5['dishes'])} 道菜, 蛋白质{r5['total_protein']}g")
    print(f"  [PASS] 返回结构含: {sorted(r5.keys())}")

    # ============================================================
    print("\n" + "=" * 50)
    print("8. @tool preferences 生效（偏好影响补足选择）")
    print("=" * 50)
    r_light = optimize_meal_tool.invoke({"budget": 20, "calorie_limit": 800,
                                         "preferences": "清淡"})
    r_spicy = optimize_meal_tool.invoke({"budget": 20, "calorie_limit": 800,
                                         "preferences": "辣"})
    assert r_light["balance_ok"] and r_spicy["balance_ok"]
    names_light = [d["name"] for d in r_light["dishes"]]
    names_spicy = [d["name"] for d in r_spicy["dishes"]]
    # 偏好应导致补足菜品不同（清淡偏素菜 vs 辣偏重口）
    assert names_light != names_spicy, f"偏好应影响搭配: {names_light} vs {names_spicy}"
    print(f"  [PASS] 清淡偏好搭配: {names_light}")
    print(f"  [PASS] 辣偏好搭配: {names_spicy}")
    print("  [PASS] optimize_meal_tool 的 preferences 已生效")

    print("\n" + "=" * 50)
    print("全部验证通过")
    print("=" * 50)

finally:
    if os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass