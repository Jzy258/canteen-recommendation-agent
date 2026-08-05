"""会话管理（B 拥有 · D7，A v1.3 扩展为 SQLite 持久化）

- 会话隔离：session_id → 消息历史
- **历史持久化**：消息写入 SQLite（chat_session/chat_message 表），
  服务重启 / 跨请求均可恢复历史对话
- 内存缓存：加速热会话读取；缓存未命中时回源数据库
- 线程安全（FastAPI 多线程处理请求）
"""
import threading
import time
from datetime import datetime, timedelta

from langchain_core.messages import AIMessage, HumanMessage


class SessionStore:
    def __init__(self, max_history: int = 20, ttl_minutes: int = 60 * 24,
                 max_sessions: int = 1000):
        self._max_history = max_history
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_sessions = max_sessions
        # 内存缓存：sid -> {"messages": [...], "last_access": float}
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _db(self):
        from db import get_db
        return get_db()

    def get(self, session_id: str) -> list:
        """获取会话历史（优先缓存，未命中从数据库回源）。"""
        with self._lock:
            entry = self._cache.get(session_id)
            if entry is not None:
                entry["last_access"] = time.time()
                return entry["messages"]
        # 缓存未命中 → 从库读取（langchain 消息对象）
        try:
            rows = self._db().get_chat_messages(session_id)
            msgs = []
            for r in rows:
                if r["role"] == "user":
                    msgs.append(HumanMessage(content=r["content"]))
                else:
                    msgs.append(AIMessage(content=r["content"]))
            with self._lock:
                self._cache[session_id] = {"messages": msgs,
                                           "last_access": time.time()}
                self._trim_cache_locked()
            return msgs
        except Exception:
            return []

    def append(self, session_id: str, human_text: str, ai_text: str,
               user_id: int | None = None):
        """追加一轮对话：写入数据库 + 更新缓存。"""
        db = self._db()
        db.add_chat_message(session_id, "user", human_text, user_id=user_id)
        db.add_chat_message(session_id, "assistant", ai_text, user_id=user_id)
        with self._lock:
            entry = self._cache.get(session_id)
            if entry is None:
                entry = {"messages": [], "last_access": time.time()}
                self._cache[session_id] = entry
            entry["messages"].append(HumanMessage(content=human_text))
            entry["messages"].append(AIMessage(content=ai_text))
            # 内存缓存仍裁剪，库中全量保留
            if len(entry["messages"]) > self._max_history:
                entry["messages"] = entry["messages"][-self._max_history:]
            entry["last_access"] = time.time()

    def clear(self, session_id: str, user_id: int | None = None):
        """清除会话（内存 + 数据库）。"""
        with self._lock:
            self._cache.pop(session_id, None)
        try:
            self._db().delete_chat_session(session_id, user_id=user_id)
        except Exception:
            pass

    def clear_all(self):
        with self._lock:
            self._cache.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._cache)

    def _trim_cache_locked(self):
        """内存缓存超上限时 LRU 淘汰（仅淘汰缓存，不影响数据库）。"""
        if len(self._cache) <= self._max_sessions:
            return
        sorted_sids = sorted(self._cache,
                             key=lambda s: self._cache[s]["last_access"])
        for sid in sorted_sids[:len(self._cache) - self._max_sessions]:
            del self._cache[sid]


# 全局单例（供 main 使用）
session_store = SessionStore()
