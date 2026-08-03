import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from tools.optimizer import optimize_meal_tool


def test_optimize_with_constraints():
    r = optimize_meal_tool.invoke({"budget": 20, "calorie_limit": 800})
    assert r["dishes"], "should return a meal combination"
    assert r["total_price"] <= 20, f"price {r['total_price']} exceeds budget"
    assert r["total_calories"] <= 800, f"calories {r['total_calories']} exceeds limit"
    print(f"  dishes: {[d['name'] for d in r['dishes']]}")
    print(f"  total: {r['total_price']}元 / {r['total_calories']}kcal / {r['total_protein']}g protein")


def test_optimize_balance():
    r = optimize_meal_tool.invoke({"budget": 25, "calorie_limit": 900})
    cats = {d["category"] for d in r["dishes"]}
    assert "荤菜" in cats and "素菜" in cats and "主食" in cats, f"missing category: {cats}"
    print(f"  categories: {cats}")
    print(f"  balance_ok: {r['balance_ok']}, reason: {r['reason']}")


def test_optimize_budget_too_small():
    r = optimize_meal_tool.invoke({"budget": 2, "calorie_limit": 500})
    # too-small budget: either empty solution or an unbalanced partial result
    assert not r["dishes"] or not r["balance_ok"], "infeasible budget should be flagged"
    assert r["reason"], "should explain reason"
    print(f"  infeasible handled: {r['reason']}")


def test_optimize_returns_metrics():
    r = optimize_meal_tool.invoke({"budget": 30, "calorie_limit": 1000})
    for k in ["total_price", "total_calories", "total_protein", "total_carbs", "total_fat",
              "categories", "budget", "calorie_limit", "balance_ok", "reason"]:
        assert k in r, f"missing key {k}"
    print("  all metric keys present")


if __name__ == "__main__":
    tests = [
        test_optimize_with_constraints,
        test_optimize_balance,
        test_optimize_budget_too_small,
        test_optimize_returns_metrics,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} - {e}")
    print(f"\n{passed}/{len(tests)} tests passed")