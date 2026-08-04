import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from tools.nutrition import get_dish_nutrition


def test_exact_name():
    r = get_dish_nutrition.invoke({"dish_name": "红烧肉"})
    assert "error" not in r, f"should find dish: {r}"
    assert r["name"] == "红烧肉"
    for k in ["calories", "protein", "carbs", "fat", "price"]:
        assert k in r, f"missing {k}"
    assert r["calories"] > 0 and r["protein"] > 0
    print(f"  红烧肉: {r['calories']}kcal, protein={r['protein']}g, price={r['price']}元")


def test_fuzzy_name():
    r = get_dish_nutrition.invoke({"dish_name": "红烧"})
    assert "error" not in r, f"fuzzy should match: {r}"
    print(f"  fuzzy '红烧': {r['name']}")


def test_not_found():
    r = get_dish_nutrition.invoke({"dish_name": "不存在的菜"})
    assert "error" in r, "should return error for missing dish"
    assert "未找到" in r["error"]
    print(f"  not found handled: {r['error']}")


def test_fields_present():
    r = get_dish_nutrition.invoke({"dish_name": "宫保鸡丁"})
    for k in ["name", "calories", "protein", "carbs", "fat", "price", "category", "source"]:
        assert k in r, f"missing key {k}"
    print(f"  fields: {sorted(r.keys())}")


def test_agent_registered():
    from agent.agent import tools
    names = [t.name for t in tools]
    assert "get_dish_nutrition" in names, "tool should be registered in agent"
    print("  get_dish_nutrition registered in agent")


if __name__ == "__main__":
    tests = [
        test_exact_name,
        test_fuzzy_name,
        test_not_found,
        test_fields_present,
        test_agent_registered,
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