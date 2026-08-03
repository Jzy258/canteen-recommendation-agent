import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from tools.scoring import recommend


def test_recommend_with_budget():
    r = recommend.invoke({"budget": 10, "top_k": 3})
    assert len(r) == 3, "Should return 3 results"
    for d in r:
        assert d["price"] <= 10, f"Price {d['price']} exceeds budget 10"
    assert r[0]["score"] >= r[1]["score"], "Should be sorted by score"
    assert all(k in r[0] for k in ["score", "budget_score", "nutrition_score", "preference_score"])
    print(f"  budget 10: {[d['name'] for d in r]}")
    print(f"  scores: {[d['score'] for d in r]}")


def test_recommend_with_health_goal():
    r = recommend.invoke({"health_goals": "高蛋白", "top_k": 3})
    assert len(r) == 3
    assert all("score" in d for d in r)
    print(f"  health 高蛋白: {[d['name'] for d in r]}")
    print(f"  scores: {[d['score'] for d in r]}")


def test_recommend_with_preferences():
    r = recommend.invoke({"preferences": "辣", "top_k": 3})
    assert len(r) == 3
    print(f"  flavor 辣: {[d['name'] for d in r]}")
    print(f"  scores: {[d['score'] for d in r]}")


def test_recommend_all_params():
    r = recommend.invoke({
        "budget": 12,
        "preferences": "辣",
        "health_goals": "高蛋白",
        "top_k": 5,
    })
    assert len(r) == 5
    for d in r:
        assert d["score"] >= 0
        assert d["price"] <= 12, "budget hard constraint"
    print(f"  all params: {[d['name'] for d in r]}")
    print(f"  scores: {[d['score'] for d in r]}")


def test_recommend_default():
    r = recommend.invoke({})
    assert len(r) == 5, "Default top_k should be 5"
    assert all("score" in d for d in r)
    print(f"  default: {len(r)} results, top score={r[0]['score']}")


def test_recommend_score_range():
    r = recommend.invoke({"budget": 15, "top_k": 10})
    for d in r:
        assert 0 <= d["score"] <= 1, f"score {d['score']} out of [0,1]"
    print("  scores all within [0,1]")


if __name__ == "__main__":
    tests = [
        test_recommend_with_budget,
        test_recommend_with_health_goal,
        test_recommend_with_preferences,
        test_recommend_all_params,
        test_recommend_default,
        test_recommend_score_range,
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