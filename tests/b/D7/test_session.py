import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from agent.session import SessionStore


def test_get_creates_empty():
    s = SessionStore(max_history=4)
    h = s.get("new-session")
    assert h == [], "new session should be empty"
    print("  get creates empty session: OK")


def test_append_and_get():
    s = SessionStore(max_history=4)
    s.append("sid", "你好", "你好！")
    h = s.get("sid")
    assert len(h) == 2, "should have human + ai"
    assert h[0].content == "你好"
    print(f"  append+get: {len(h)} messages")


def test_history_trim():
    s = SessionStore(max_history=4)
    for i in range(5):
        s.append("sid", f"q{i}", f"a{i}")
    h = s.get("sid")
    assert len(h) == 4, "history should be trimmed to max_history"
    print(f"  history trimmed to {len(h)}")


def test_clear():
    s = SessionStore()
    s.append("sid", "hi", "hello")
    s.clear("sid")
    assert s.count() == 0
    print("  clear session: OK")


def test_max_sessions_lru():
    s = SessionStore(max_history=2, max_sessions=3)
    for i in range(5):
        s.append(f"s{i}", "hi", "hello")
    assert s.count() == 3, f"should keep only 3 sessions, got {s.count()}"
    print(f"  max sessions LRU: kept {s.count()}")


if __name__ == "__main__":
    tests = [
        test_get_creates_empty,
        test_append_and_get,
        test_history_trim,
        test_clear,
        test_max_sessions_lru,
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