"""C · D1 阶段：REST 契约冒烟测试（针对运行中的后端）

前置：后端已启动（uv run python backend/main.py，端口默认 8000）。
运行：python tests/c/D1/test_contract.py [port]
覆盖：/health、空消息 400、/chat 返回 reply+session_id、CORS。
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

PORT = 8000
BASE = f"http://localhost:{PORT}"


def _post(path: str, payload: dict, timeout: int = 60):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def test_health():
    resp = urllib.request.urlopen(f"{BASE}/health", timeout=5)
    assert json.loads(resp.read().decode()) == {"status": "ok"}


def test_empty_message_rejected():
    try:
        _post("/chat", {"message": ""}, timeout=5)
        raise AssertionError("空消息应返回 400")
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_chat_returns_session_id():
    resp = _post("/chat", {"message": "你好"})
    body = json.loads(resp.read().decode())
    assert "reply" in body and body["reply"]
    assert "session_id" in body and body["session_id"]


def test_chat_session_stable():
    """同一 session_id 两轮对话，session_id 原值返回（多轮记忆基础）。"""
    resp = _post("/chat", {"message": "有什么菜？", "session_id": "c-test-session-1"})
    body = json.loads(resp.read().decode())
    assert body["session_id"] == "c-test-session-1"


def test_cors_header():
    req = urllib.request.Request(
        f"{BASE}/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    resp = urllib.request.urlopen(req, timeout=5)
    allow_origin = resp.headers.get("Access-Control-Allow-Origin")
    assert allow_origin in ("*", "http://localhost:5173")


def run_all():
    tests = [
        test_health,
        test_empty_message_rejected,
        test_chat_returns_session_id,
        test_chat_session_stable,
        test_cors_header,
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
    return passed == len(tests)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        PORT = int(sys.argv[1])
        BASE = f"http://localhost:{PORT}"
    sys.exit(0 if run_all() else 1)
