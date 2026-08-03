import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from langchain_core.messages import AIMessage
from fastapi.testclient import TestClient


class FakeAgent:
    def invoke(self, state):
        n = len(state["messages"])
        text = f"回复内容-消息数{n}：" + "流式测试内容" * 3
        return {"messages": [AIMessage(content=text)]}


def build_client():
    import main as main_mod
    from agent.session import session_store
    main_mod.agent = FakeAgent()
    session_store.clear_all()
    return TestClient(main_mod.app)


def test_stream_returns_sse():
    c = build_client()
    with c.stream("POST", "/chat/stream", json={"message": "你好", "session_id": "s1"}) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        body = r.read().decode("utf-8")
    assert "data:" in body
    print(f"  SSE content-type OK, body len={len(body)}")


def test_stream_has_session_and_done():
    c = build_client()
    with c.stream("POST", "/chat/stream", json={"message": "你好", "session_id": "s2"}) as r:
        body = r.read().decode("utf-8")
    events = [json.loads(ln[5:]) for ln in body.splitlines() if ln.startswith("data:")]
    assert any(e.get("type") == "session" for e in events), "should send session event"
    assert events[-1].get("type") == "done", "last event should be done"
    deltas = [e for e in events if e.get("type") == "delta"]
    assert len(deltas) > 0, "should have content deltas"
    full = "".join(d["content"] for d in deltas)
    assert "流式" in full, "deltas should assemble to full reply"
    print(f"  stream events: {len(events)} (session + {len(deltas)} deltas + done)")


def test_stream_empty_rejected():
    c = build_client()
    r = c.post("/chat/stream", json={"message": " "})
    assert r.status_code == 400
    print("  empty stream message rejected")


def test_session_isolation():
    c = build_client()
    a1 = c.post("/chat", json={"message": "A1", "session_id": "iso-a"}).json()
    b1 = c.post("/chat", json={"message": "B1", "session_id": "iso-b"}).json()
    assert a1["reply"] == "回复内容-消息数1：流式测试内容流式测试内容流式测试内容"
    assert b1["reply"] == "回复内容-消息数1：流式测试内容流式测试内容流式测试内容"
    a2 = c.post("/chat", json={"message": "A2", "session_id": "iso-a"}).json()
    assert a2["reply"].startswith("回复内容-消息数3"), "session A should accumulate history"
    print("  session isolation + memory OK")


if __name__ == "__main__":
    tests = [
        test_stream_returns_sse,
        test_stream_has_session_and_done,
        test_stream_empty_rejected,
        test_session_isolation,
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