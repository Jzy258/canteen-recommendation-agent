import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from tools.search import search_dish, get_all_dishes


def test_keyword_search():
    r = search_dish.invoke({"keyword": "鸡"})
    assert len(r) > 0, "Should find dishes with 鸡"
    print(f"  keyword '鸡': {len(r)} results")


def test_exact_name_search():
    r = search_dish.invoke({"keyword": "红烧肉"})
    assert any(d["name"] == "红烧肉" for d in r), "Should find 红烧肉"
    print(f"  exact '红烧肉': {len(r)} result")


def test_all_dishes_count():
    r = get_all_dishes.invoke({})
    assert len(r) >= 30, f"Should have at least 30 dishes, got {len(r)}"
    print(f"  total dishes: {len(r)}")


def test_dish_has_price():
    r = get_all_dishes.invoke({})
    assert all("price" in d for d in r), "All dishes should have price"
    print("  price field: OK")


def test_dish_has_nutrition():
    r = get_all_dishes.invoke({})
    for d in r:
        assert all(k in d for k in ["calories", "protein", "carbs", "fat"]), (
            f"Missing nutrition in {d['name']}"
        )
    print("  nutrition fields: OK")


def test_no_match_returns_empty():
    r = search_dish.invoke({"keyword": "xxxxxxxx"})
    assert len(r) == 0, "Should return empty for no match"
    print("  no match: OK")


def test_dish_has_source():
    r = get_all_dishes.invoke({})
    assert all("source" in d for d in r), "All dishes should have source"
    print("  source field: OK")


def test_dish_has_category():
    r = get_all_dishes.invoke({})
    assert all("category" in d for d in r), "All dishes should have category"
    print("  category field: OK")


if __name__ == "__main__":
    tests = [
        test_keyword_search,
        test_exact_name_search,
        test_all_dishes_count,
        test_dish_has_price,
        test_dish_has_nutrition,
        test_no_match_returns_empty,
        test_dish_has_source,
        test_dish_has_category,
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