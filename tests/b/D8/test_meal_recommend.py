import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

import tools.meal_time as mt
from tools.meal_recommend import recommend_for_meal


def test_breakfast_time():
    mt.now_override = datetime(2026, 8, 4, 7, 30)
    assert mt.current_meal() == "breakfast"
    print("  07:30 -> breakfast")
    mt.now_override = None


def test_lunch_time():
    mt.now_override = datetime(2026, 8, 4, 12, 0)
    assert mt.current_meal() == "lunch"
    print("  12:00 -> lunch")
    mt.now_override = None


def test_dinner_time():
    mt.now_override = datetime(2026, 8, 4, 18, 30)
    assert mt.current_meal() == "dinner"
    print("  18:30 -> dinner")
    mt.now_override = None


def test_snack_time():
    mt.now_override = datetime(2026, 8, 4, 23, 0)
    assert mt.current_meal() == "snack"
    print("  23:00 -> snack")
    mt.now_override = None


def test_meal_label():
    assert mt.meal_label("breakfast") == "早餐"
    assert mt.meal_label("lunch") == "午餐"
    assert mt.meal_label("dinner") == "晚餐"
    print("  labels: 早餐/午餐/晚餐")


def test_recommend_for_meal_structure():
    mt.now_override = datetime(2026, 8, 4, 12, 0)
    try:
        r = recommend_for_meal.invoke({"top_k": 3})
        assert r["meal"] == "lunch"
        assert r["meal_label"] == "午餐"
        assert "dishes" in r and len(r["dishes"]) > 0
        for d in r["dishes"]:
            assert "score" in d and "name" in d
        print(f"  recommend_for_meal: {r['meal_label']}, {len(r['dishes'])} dishes, source={r['source']}")
    finally:
        mt.now_override = None


def test_suggestion_contains_meal_label():
    mt.now_override = datetime(2026, 8, 4, 18, 30)
    try:
        r = recommend_for_meal.invoke({"top_k": 3})
        assert "现在是晚餐时间" in r["suggestion"], f"suggestion should mention meal: {r['suggestion']}"
        print(f"  suggestion: {r['suggestion']}")
    finally:
        mt.now_override = None


def test_recommend_budget_constraint():
    mt.now_override = datetime(2026, 8, 4, 12, 0)
    try:
        r = recommend_for_meal.invoke({"budget": 5, "top_k": 5})
        for d in r["dishes"]:
            assert d["price"] <= 5, f"price {d['price']} exceeds budget"
        print(f"  budget=5: {len(r['dishes'])} dishes all <= 5元")
    finally:
        mt.now_override = None


if __name__ == "__main__":
    tests = [
        test_breakfast_time,
        test_lunch_time,
        test_dinner_time,
        test_snack_time,
        test_meal_label,
        test_recommend_for_meal_structure,
        test_suggestion_contains_meal_label,
        test_recommend_budget_constraint,
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