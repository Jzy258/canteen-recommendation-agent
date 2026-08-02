import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from tools.recommend import recommend_dishes


def test_recommend_with_budget():
    r = recommend_dishes.invoke({"budget": 10, "top_n": 3})
    assert len(r) == 3, "Should return 3 results"
    for d in r:
        assert d["price"] <= 10, f"Price {d['price']} exceeds budget 10"
    assert r[0]["recommend_score"] >= r[1]["recommend_score"], "Should be sorted by score"
    print(f"  budget 10: {[d['name'] for d in r]}")
    print(f"  scores: {[d['recommend_score'] for d in r]}")


def test_recommend_with_category():
    r = recommend_dishes.invoke({"pref_category": "素菜", "top_n": 3})
    assert len(r) == 3
    for d in r:
        assert "recommend_score" in d
    print(f"  category 素菜: {[d['name'] for d in r]}")
    print(f"  scores: {[d['recommend_score'] for d in r]}")


def test_recommend_with_health_goal():
    r = recommend_dishes.invoke({"health_goal": "高蛋白", "top_n": 3})
    assert len(r) == 3
    print(f"  health 高蛋白: {[d['name'] for d in r]}")
    print(f"  scores: {[d['recommend_score'] for d in r]}")


def test_recommend_with_flavor():
    r = recommend_dishes.invoke({"pref_flavor": "辣", "top_n": 3})
    assert len(r) == 3
    print(f"  flavor 辣: {[d['name'] for d in r]}")
    print(f"  scores: {[d['recommend_score'] for d in r]}")


def test_recommend_all_params():
    r = recommend_dishes.invoke({
        "budget": 12,
        "pref_category": "荤菜",
        "pref_flavor": "辣",
        "health_goal": "高蛋白",
        "top_n": 5,
    })
    assert len(r) == 5
    for d in r:
        assert d["recommend_score"] >= 0
    print(f"  all params: {[d['name'] for d in r]}")
    print(f"  scores: {[d['recommend_score'] for d in r]}")


def test_recommend_default():
    r = recommend_dishes.invoke({})
    assert len(r) == 5, "Default top_n should be 5"
    assert all(d["recommend_score"] == 50.0 for d in r), "Default score should be 50"
    print(f"  default: {len(r)} results, score={r[0]['recommend_score']}")


if __name__ == "__main__":
    tests = [
        test_recommend_with_budget,
        test_recommend_with_category,
        test_recommend_with_health_goal,
        test_recommend_with_flavor,
        test_recommend_all_params,
        test_recommend_default,
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