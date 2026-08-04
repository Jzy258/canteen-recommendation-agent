"""请求监控中间件：日志 + 耗时 + Token 统计（B 拥有 · D5）。

- 记录每次请求的 method / path / status / 耗时（ms）
- 累计 Token 用量（LLM 会话 token 估算，存内存 + 可落盘 JSON）
- 提供 /metrics 查看入口（FastAPI 依赖注入式）
"""
import json
import os
import time
from collections import defaultdict
from datetime import datetime

# 运行期累计统计（进程内共享）
_stats = {
    "requests": 0,
    "errors": 0,
    "total_time_ms": 0.0,
    "total_tokens": 0,
    "by_path": defaultdict(int),
    "token_history": [],  # [{time, tokens}]
}

# 默认 metrics 文件基于 backend/ 包根目录解析（与运行目录无关）
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATS_FILE = os.getenv("METRICS_FILE") or os.path.join(_BACKEND_ROOT, "data", "metrics.json")
_MAX_TOKEN_HISTORY = 1000  # 内存中保留的 token 记录条数上限


def _persist():
    try:
        data = {
            "requests": _stats["requests"],
            "errors": _stats["errors"],
            "total_time_ms": round(_stats["total_time_ms"], 2),
            "total_tokens": _stats["total_tokens"],
            "by_path": dict(_stats["by_path"]),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        os.makedirs(os.path.dirname(_STATS_FILE), exist_ok=True)
        with open(_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_tokens(count: int):
    """外部（Agent 层）上报本次 LLM 调用消耗的 token 数。"""
    if count <= 0:
        return
    _stats["total_tokens"] += count
    _stats["token_history"].append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "tokens": count,
    })
    # 限制历史条数，防止内存无限增长
    if len(_stats["token_history"]) > _MAX_TOKEN_HISTORY:
        _stats["token_history"] = _stats["token_history"][-_MAX_TOKEN_HISTORY:]
    _persist()


def get_metrics() -> dict:
    """返回统计快照。"""
    return {
        "requests": _stats["requests"],
        "errors": _stats["errors"],
        "avg_time_ms": round(_stats["total_time_ms"] / max(_stats["requests"], 1), 2),
        "total_time_ms": round(_stats["total_time_ms"], 2),
        "total_tokens": _stats["total_tokens"],
        "by_path": dict(_stats["by_path"]),
    }


class RequestMetricsMiddleware:
    """Starlette 中间件：请求日志 + 耗时统计。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start = time.perf_counter()
        status_holder = {"status": 500}

        async def _send(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception:
            _stats["errors"] += 1
            raise
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            _stats["requests"] += 1
            _stats["total_time_ms"] += elapsed
            path = scope.get("path", "?")
            _stats["by_path"][path] += 1
            print(f"[metrics] {scope.get('method','?')} {path} -> "
                  f"{status_holder['status']} ({elapsed:.1f}ms)")
            _persist()


def make_middleware(app):
    """创建中间件实例（FastAPI app.add_middleware 需要类而非实例）。"""
    return RequestMetricsMiddleware(app)