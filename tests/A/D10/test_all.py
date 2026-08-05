"""
A · D10 历史对话交付物验证
覆盖：chat_session/chat_message 表 / SessionStore SQLite 持久化 / 历史接口 / 会话列表
"""
import os
import sys
import tempfile
import sqlite3

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))

passes = 0
fails = 0

def check(name, cond, detail=""):
    global passes, fails
    if cond:
        passes += 1
        print(f"  [PASS] {name}")
    else:
        fails += 1
        print(f"  [FAIL] {name} {detail}")

print("=" * 55)
print("交付物 1: schema.sql v1.3（chat 表）")
print("=" * 55)
schema = open(os.path.join(_PROJECT_ROOT, "backend", "db", "schema.sql"),
              encoding="utf-8").read()
check("schema 版本 v1.3", "v1.3" in schema)
check("含 chat_session 表", "CREATE TABLE IF NOT EXISTS chat_session" in schema)
check("含 chat_message 表", "CREATE TABLE IF NOT EXISTS chat_message" in schema)
check("chat_message 外键级联", "REFERENCES chat_session(session_id) ON DELETE CASCADE" in schema)

print("=" * 55)
print("交付物 2: db.py 历史对话接口")
print("=" * 55)
db_code = open(os.path.join(_PROJECT_ROOT, "backend", "db", "db.py"),
               encoding="utf-8").read()
for m in ["_migrate_v13", "add_chat_message", "get_chat_messages",
          "list_chat_sessions", "delete_chat_session"]:
    check(f"db.py 含 {m}", f"def {m}" in db_code)

from db import SQLiteDatabase, DatabaseInterface
impl = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
abstr = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
check("接口抽象与实现一致", abstr.issubset(impl))

print("=" * 55)
print("交付物 3: 历史消息写入与读取")
print("=" * 55)
tmp_db = os.path.join(tempfile.gettempdir(), "test_d10.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
db = SQLiteDatabase(tmp_db)
db.add_chat_message("sess-1", "user", "今天吃什么？")
db.add_chat_message("sess-1", "assistant", "推荐红烧肉和米饭")
msgs = db.get_chat_messages("sess-1")
check("写入两条消息", len(msgs) == 2)
check("顺序正确（user 在前）", msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant")
check("内容保留", msgs[1]["content"] == "推荐红烧肉和米饭")

print("=" * 55)
print("交付物 4: SessionStore SQLite 持久化")
print("=" * 55)
# 复用临时库：SessionStore 用 db.get_db() 单例，先注入临时库
import db as dbmod
from agent.session import SessionStore
_db_tmp = SQLiteDatabase(tmp_db)
dbmod._db_instance = _db_tmp
store = SessionStore()
store.append("sess-persist", "你好", "你好！有什么可以帮你？")
# 新实例（模拟重启）应能从库恢复
store2 = SessionStore()
hist = store2.get("sess-persist")
check("新实例可恢复历史", len(hist) == 2)
check("消息内容正确", hist[0].content == "你好" and hist[1].content == "你好！有什么可以帮你？")
# 库中确实有
rows = db.get_chat_messages("sess-persist")
check("消息已入库", len(rows) == 2)

print("=" * 55)
print("交付物 5: 会话列表 / 删除")
print("=" * 55)
db.add_chat_message("sess-a", "user", "第一条会话")
sessions = db.list_chat_sessions(user_id=None)
check("列表包含会话", any(s["session_id"] == "sess-a" for s in sessions))
check("列表按更新时间倒序", sessions[0]["updated_at"] >= sessions[-1]["updated_at"])
db.delete_chat_session("sess-a")
check("删除后消息级联清除", db.get_chat_messages("sess-a") == [])

print("=" * 55)
print("交付物 6: v1.3 迁移幂等")
print("=" * 55)
# 老库（有 dish 无 chat 表）
old_db = os.path.join(tempfile.gettempdir(), "test_d10_old.db")
if os.path.exists(old_db):
    os.remove(old_db)
con = sqlite3.connect(old_db)
con.executescript("""
    CREATE TABLE dish (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
        calories REAL NOT NULL, protein REAL NOT NULL, carbs REAL NOT NULL, fat REAL NOT NULL,
        price REAL NOT NULL, category TEXT NOT NULL, flavor_tags TEXT DEFAULT '',
        serving_grams REAL DEFAULT 150, source TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')));
""")
con.commit()
con.close()
db_old = SQLiteDatabase(old_db)
con = sqlite3.connect(old_db)
chat_tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'chat_%'")]
check("老库迁移建 chat 表", sorted(chat_tables) == ["chat_message", "chat_session"])
con.close()
# 幂等：再次实例化
db_old2 = SQLiteDatabase(old_db)
con2 = sqlite3.connect(old_db)
check("重复迁移幂等", len(con2.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_session'").fetchall()) == 1)
con2.close()

print("=" * 55)
print("交付物 7: main.py 历史接口注册")
print("=" * 55)
main_code = open(os.path.join(_PROJECT_ROOT, "backend", "main.py"),
                 encoding="utf-8").read()
for route in ["/sessions", "get_session_messages", "delete_session", "list_sessions"]:
    check(f"main.py 含 {route}", route in main_code)

print("=" * 55)
print(f"结果: {passes} passed, {fails} failed")
print("=" * 55)
if fails:
    sys.exit(1)
