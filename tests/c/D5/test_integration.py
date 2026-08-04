"""C · D5 阶段：前后端集成验证（针对运行中的后端）

前置：后端已启动（uv run python backend/main.py，端口 8000）。
运行：python tests/c/D5/test_integration.py [port]
覆盖：/trend 结构化数据、/chat/stream SSE 三段事件、/metrics。
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

PORT = 8000
BASE = f"http://localhost:{PORT}"


def _get(path: str, timeout: int = 10):
    return urllib.request.urlopen(f"{BASE}{path}", timeout=timeout)


def _post_stream(payload: dict, timeout: int = 60):
    req = urllib.request.Request(
        f"{BASE}/chat/stream",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def test_trend_structured():
    resp = _get("/trend?days=7&end_date=2026-08-03")
    data = json.loads(resp.read().decode())
    assert isinstance(data, list) and len(data) == 7, "应返回连续 7 天"
    keys = {"date", "total_calories", "total_protein", "total_carbs", "total_fat", "dish_count"}
    for point in data:
        assert keys <= set(point), f"趋势点缺字段: {point}"
    assert data[0]["date"] == "2026-07-28"
    assert data[-1]["date"] == "2026-08-03"


def test_trend_default_days():
    resp = _get("/trend")
    data = json.loads(resp.read().decode())
    assert len(data) == 7, "默认应为 7 天"


def test_chat_stream_sse():
    resp = _post_stream({"message": "有什么菜？", "session_id": "c-d5-integration"})
    body = resp.read().decode()
    frames = [f for f in body.split("\n\n") if f.strip()]
    types = []
    session_seen = False
    done_seen = False
    for frame in frames:
        line = frame.strip()
        if not line.startswith("data:"):
            continue
        evt = json.loads(line[5:].strip())
        types.append(evt.get("type"))
        if evt.get("type") == "session":
            assert evt.get("session_id")
            session_seen = True
        if evt.get("type") == "done":
            done_seen = True
    assert session_seen, "缺少 session 事件"
    assert done_seen, "缺少 done 事件"
    assert "delta" in types, "缺少 delta 事件"
    assert types.index("session") < types.index("done"), "事件顺序错误"


def test_metrics_available():
    resp = _get("/metrics")
    data = json.loads(resp.read().decode())
    for k in ["requests", "avg_time_ms", "total_tokens"]:
        assert k in data, f"metrics 缺字段 {k}"


def run_all():
    tests = [
        ("趋势接口 /trend", test_trend_structured),
        ("趋势默认参数", test_trend_default_days),
        ("流式 SSE 三段事件", test_chat_stream_sse),
        ("中间件 /metrics", test_metrics_available),
    ]
    passed = 0
    for name, t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            print(f"  FAIL: {name} - {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        PORT = int(sys.argv[1])
        BASE = f"http://localhost:{PORT}"
    sys.exit(0 if run_all() else 1)
