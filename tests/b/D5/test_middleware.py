import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from middleware import add_tokens, get_metrics, RequestMetricsMiddleware


def test_add_tokens():
    before = get_metrics()["total_tokens"]
    add_tokens(50)
    after = get_metrics()["total_tokens"]
    assert after == before + 50, "tokens should accumulate"
    print(f"  tokens: {before} -> {after}")


def test_get_metrics_shape():
    m = get_metrics()
    for k in ["requests", "errors", "avg_time_ms", "total_time_ms", "total_tokens", "by_path"]:
        assert k in m, f"missing key {k}"
    print(f"  metrics keys: {sorted(m.keys())}")


def test_ignore_zero_tokens():
    before = get_metrics()["total_tokens"]
    add_tokens(0)
    add_tokens(-5)
    assert get_metrics()["total_tokens"] == before, "non-positive tokens ignored"
    print("  non-positive tokens ignored")


def test_middleware_class_buildable():
    mw = RequestMetricsMiddleware(object())
    assert mw is not None
    print("  middleware constructible")


if __name__ == "__main__":
    tests = [
        test_add_tokens,
        test_get_metrics_shape,
        test_ignore_zero_tokens,
        test_middleware_class_buildable,
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