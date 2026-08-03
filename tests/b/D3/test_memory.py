import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from langchain_core.messages import AIMessage
from fastapi.testclient import TestClient


class FakeAgent:
    def invoke(self, state):
        # echo how many messages were passed in, to verify history accumulates
        n = len(state["messages"])
        return {"messages": [AIMessage(content=f"seen {n} messages")]}


def build_client():
    import main as main_mod
    from agent.session import session_store
    main_mod.agent = FakeAgent()
    session_store.clear_all()
    return TestClient(main_mod.app)


def test_health():
    c = build_client()
    r = c.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    print("  health: OK")


def test_empty_message():
    c = build_client()
    r = c.post("/chat", json={"message": "  "})
    assert r.status_code == 400
    print("  empty message rejected: OK")


def test_multi_turn_memory():
    c = build_client()
    sid = "mem-test-1"
    # turn 1: history has 1 human message
    r1 = c.post("/chat", json={"message": "第一句", "session_id": sid})
    assert r1.status_code == 200
    assert r1.json()["reply"] == "seen 1 messages"
    # turn 2: history should accumulate to 3 (human+ai+human)
    r2 = c.post("/chat", json={"message": "第二句", "session_id": sid})
    assert r2.json()["reply"] == "seen 3 messages"
    # turn 3: now 5
    r3 = c.post("/chat", json={"message": "第三句", "session_id": sid})
    assert r3.json()["reply"] == "seen 5 messages"
    print("  multi-turn memory accumulates: OK")


def test_session_isolation():
    c = build_client()
    a = c.post("/chat", json={"message": "A1", "session_id": "iso-a"}).json()
    b = c.post("/chat", json={"message": "B1", "session_id": "iso-b"}).json()
    assert a["reply"] == "seen 1 messages"
    assert b["reply"] == "seen 1 messages"
    a2 = c.post("/chat", json={"message": "A2", "session_id": "iso-a"}).json()
    assert a2["reply"] == "seen 3 messages", "session A should remember its own history"
    print("  session isolation: OK")


def test_no_session_autogen():
    c = build_client()
    r = c.post("/chat", json={"message": "hi"})
    assert r.json()["session_id"], "should auto-generate session_id"
    print("  session_id auto-gen: OK")


if __name__ == "__main__":
    tests = [
        test_health,
        test_empty_message,
        test_multi_turn_memory,
        test_session_isolation,
        test_no_session_autogen,
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