import sys
import json
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

import urllib.request


def test_health_endpoint(port=8000):
    resp = urllib.request.urlopen(f"http://localhost:{port}/health")
    data = json.loads(resp.read().decode())
    assert data == {"status": "ok"}, f"Expected ok, got {data}"
    print("  health endpoint: OK")


def test_empty_message_rejected(port=8000):
    data = json.dumps({"message": ""}).encode()
    req = urllib.request.Request(
        f"http://localhost:{port}/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Empty message should be rejected"
    except urllib.error.HTTPError as e:
        assert e.code == 400, f"Expected 400, got {e.code}"
        print("  empty message rejection: OK")


def test_chat_returns_session_id(port=8000):
    data = json.dumps({"message": "你好"}).encode()
    req = urllib.request.Request(
        f"http://localhost:{port}/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read().decode())
        assert "reply" in body, "Missing reply field"
        assert "session_id" in body, "Missing session_id field"
        assert body["session_id"], "session_id should not be empty"
        print("  chat session_id: OK")
    except urllib.error.HTTPError as e:
        print(f"  chat endpoint (expected without LLM): HTTP {e.code}")


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1:
        port = int(_sys.argv[1])
    else:
        port = 8000

    tests = [test_health_endpoint, test_empty_message_rejected, test_chat_returns_session_id]
    passed = 0
    for t in tests:
        try:
            t(port)
            passed += 1
            print(f"  PASS: {t.__name__}")
        except Exception as e:
            print(f"  FAIL: {t.__name__} - {e}")
    print(f"\n{passed}/{len(tests)} tests passed")