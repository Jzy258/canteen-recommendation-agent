"""会话管理（B 拥有 · D7）

- 会话隔离：session_id → 消息历史
- 内存上限 + TTL 过期清理，防止无限增长
- 线程安全（FastAPI 多线程处理请求）
"""
import threading
import time
from datetime import datetime, timedelta

from langchain_core.messages import AIMessage, HumanMessage


class SessionStore:
    def __init__(self, max_history: int = 20, ttl_minutes: int = 60,
                 max_sessions: int = 100):
        self._max_history = max_history
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_sessions = max_sessions
        self._sessions: dict[str, dict] = {}  # sid -> {"messages": [...], "last_access": float}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> list:
        """获取会话历史，不存在则创建空会话。"""
        with self._lock:
            self._cleanup_locked()
            entry = self._sessions.get(session_id)
            if entry is None:
                entry = {"messages": [], "last_access": time.time()}
                self._sessions[session_id] = entry
            entry["last_access"] = time.time()
            return entry["messages"]

    def append(self, session_id: str, human_text: str, ai_text: str):
        """追加一轮对话并裁剪历史。"""
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                entry = {"messages": [], "last_access": time.time()}
                self._sessions[session_id] = entry
            entry["messages"].append(HumanMessage(content=human_text))
            entry["messages"].append(AIMessage(content=ai_text))
            if len(entry["messages"]) > self._max_history:
                entry["messages"] = entry["messages"][-self._max_history:]
            entry["last_access"] = time.time()
            self._cleanup_locked()

    def clear(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)

    def clear_all(self):
        with self._lock:
            self._sessions.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def _cleanup_locked(self):
        """清理过期会话 + 超出上限的会话（LRU 淘汰）。"""
        now = time.time()
        expired = [sid for sid, e in self._sessions.items()
                   if now - e["last_access"] > self._ttl.total_seconds()]
        for sid in expired:
            del self._sessions[sid]
        # 仍超上限则淘汰最久未访问的
        if len(self._sessions) > self._max_sessions:
            sorted_sids = sorted(self._sessions,
                                 key=lambda s: self._sessions[s]["last_access"])
            for sid in sorted_sids[:len(self._sessions) - self._max_sessions]:
                del self._sessions[sid]


# 全局单例（供 main 使用）
session_store = SessionStore()