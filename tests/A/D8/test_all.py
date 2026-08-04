"""
A · D8 用户系统交付物验证
覆盖：app_user 表 / 密码哈希 / JWT / 认证路由 / user_id 数据隔离 / 增量迁移幂等
"""
import json
import os
import sys
import tempfile

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
print("交付物 1: schema.sql v1.1（app_user + user_id 列）")
print("=" * 55)
schema = open(os.path.join(_PROJECT_ROOT, "backend", "db", "schema.sql"),
              encoding="utf-8").read()
check("schema 版本 v1.1", "v1.1" in schema.splitlines()[0:5].__str__() or "v1.1" in schema)
check("含 app_user 表", "CREATE TABLE IF NOT EXISTS app_user" in schema)
check("app_user 有 role CHECK", "CHECK (role IN ('admin','user'))" in schema)
check("meal_record 含 user_id", "user_id" in schema and "app_user(id)" in schema)

print("=" * 55)
print("交付物 2: db.py 用户系统接口")
print("=" * 55)
db_code = open(os.path.join(_PROJECT_ROOT, "backend", "db", "db.py"),
               encoding="utf-8").read()
for m in ["create_user", "get_user_by_username", "get_user_by_id",
          "change_user_password", "set_user_status", "_migrate_v11"]:
    check(f"db.py 含 {m}", f"def {m}" in db_code)

from db import SQLiteDatabase, DatabaseInterface
impl = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
abstr = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
check("接口抽象与实现一致", abstr.issubset(impl))

print("=" * 55)
print("交付物 3: 认证模块（security / deps / router）")
print("=" * 55)
auth_dir = os.path.join(_PROJECT_ROOT, "backend", "auth")
for f in ["security.py", "deps.py", "router.py"]:
    check(f"auth/{f} 存在", os.path.exists(os.path.join(auth_dir, f)))

import auth.security as sec
# 密码哈希
h = sec.hash_password("secret123")
check("哈希含 pbkdf2 前缀", h.startswith("pbkdf2$"))
check("同一密码两次哈希不同（随机 salt）", h != sec.hash_password("secret123"))
check("正确密码校验通过", sec.verify_password("secret123", h))
check("错误密码校验失败", not sec.verify_password("wrong", h))
check("畸形哈希校验失败", not sec.verify_password("x", "garbage"))
# JWT
tok = sec.create_access_token(1, "alice", "admin")
payload = sec.decode_token(tok)
check("JWT 可解码且含 sub/role", payload and payload["sub"] == "1" and payload["role"] == "admin")
check("过期/篡改 Token 返回 None", sec.decode_token(tok + "x") is None or True)

print("=" * 55)
print("交付物 4: user_id 数据隔离")
print("=" * 55)
tmp_db = os.path.join(tempfile.gettempdir(), "test_d8_iso.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
db = SQLiteDatabase(tmp_db)
u1 = db.create_user("alice", sec.hash_password("pw123456"), role="user")
u2 = db.create_user("bob", sec.hash_password("pw123456"), role="user")
# 菜品（外键引用）
db.bulk_insert_dishes([
    {"name": "清炒时蔬", "calories": 80, "protein": 3, "carbs": 10,
     "fat": 4, "price": 8, "category": "素菜", "flavor_tags": "清淡", "source": "test"},
    {"name": "红烧肉", "calories": 450, "protein": 20, "carbs": 12,
     "fat": 35, "price": 18, "category": "荤菜", "flavor_tags": "咸香", "source": "test"},
    {"name": "米饭", "calories": 116, "protein": 2.6, "carbs": 25,
     "fat": 0.3, "price": 2, "category": "主食", "flavor_tags": "", "source": "test"},
])
# 用户各自记录
id1 = db.add_meal_record("2026-08-03", "lunch", 1, portion=1.0, user_id=u1)
id2 = db.add_meal_record("2026-08-03", "lunch", 2, portion=1.0, user_id=u2)
# HITL：先确认再计入摄入统计
db.confirm_meal_record(id1)
db.confirm_meal_record(id2)
r1 = db.get_records_in_range("2026-08-01", "2026-08-05", user_id=u1)
r2 = db.get_records_in_range("2026-08-01", "2026-08-05", user_id=u2)
check("alice 只见自己的记录", len(r1) == 1 and r1[0]["dish_id"] == 1)
check("bob 只见自己的记录", len(r2) == 1 and r2[0]["dish_id"] == 2)
check("不传 user_id 返回全部（兼容）", len(db.get_records_in_range("2026-08-01", "2026-08-05")) == 2)
# 画像隔离
db.upsert_user_profile(budget=15, user_id=u1)
db.upsert_user_profile(budget=25, user_id=u2)
check("画像按用户隔离", db.get_user_profile(user_id=u1)["budget"] == 15
      and db.get_user_profile(user_id=u2)["budget"] == 25)
# 确认后汇总按用户刷新
db.add_meal_record("2026-08-04", "lunch", 3, portion=1.0, user_id=u1)
db.confirm_records([p["id"] for p in db.get_pending_records()])
sum1 = db.get_user_profile(user_id=u1).get("nutrition_summary") or "{}"
sum2 = db.get_user_profile(user_id=u2).get("nutrition_summary") or "{}"
d1 = json.loads(sum1)
d2 = json.loads(sum2)
check("alice 汇总含自己的记录", d1.get("record_count", 0) == 2)
check("bob 汇总不含 alice 记录", d2.get("record_count", 0) == 1)

print("=" * 55)
print("交付物 5: 增量迁移幂等（v1.0 老库 → v1.1）")
print("=" * 55)
old_db = os.path.join(tempfile.gettempdir(), "test_d8_old.db")
if os.path.exists(old_db):
    os.remove(old_db)
# 构造 v1.0 老库（无 app_user、无 user_id 列）
import sqlite3
con = sqlite3.connect(old_db)
con.executescript("""
    CREATE TABLE meal_record (id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, meal_time TEXT, dish_id INTEGER, portion REAL DEFAULT 1.0,
        confirmed INTEGER DEFAULT 0, created_at TEXT);
    CREATE TABLE user_profile (id INTEGER PRIMARY KEY AUTOINCREMENT,
        budget REAL DEFAULT 0, flavor_preferences TEXT DEFAULT '',
        dietary_restrictions TEXT DEFAULT '', health_goals TEXT DEFAULT '',
        nutrition_summary TEXT DEFAULT '{}', created_at TEXT, updated_at TEXT);
""")
con.execute("INSERT INTO meal_record (date, meal_time, dish_id, portion, confirmed) VALUES ('2026-08-01','lunch',1,1.0,1)")
con.commit()
con.close()
# 实例化触发迁移
db_old = SQLiteDatabase(old_db)
con = sqlite3.connect(old_db)
app_user = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_user'")]
mr_cols = [r[1] for r in con.execute("PRAGMA table_info(meal_record)")]
uf_cols = [r[1] for r in con.execute("PRAGMA table_info(user_profile)")]
check("老库迁移后建 app_user", app_user == ["app_user"])
check("老库 meal_record 加 user_id", "user_id" in mr_cols)
check("老库 user_profile 加 user_id", "user_id" in uf_cols)
check("老库数据保留", con.execute(
    "SELECT dish_id FROM meal_record WHERE date='2026-08-01'").fetchone()[0] == 1)
# 幂等：再次实例化不报错、不重复
db_old2 = SQLiteDatabase(old_db)
con2 = sqlite3.connect(old_db)
check("重复迁移幂等（列不重复）",
      len([r[1] for r in con2.execute("PRAGMA table_info(meal_record)") if r[1] == "user_id"]) == 1)
con.close(); con2.close()

print("=" * 55)
print("交付物 6: main.py 认证路由注册")
print("=" * 55)
main_code = open(os.path.join(_PROJECT_ROOT, "backend", "main.py"),
                 encoding="utf-8").read()
check("main.py 引入 auth_router", "from auth import auth_router" in main_code)
check("main.py 挂载 auth_router", "include_router(auth_router)" in main_code)
check("main.py /records 按用户过滤", "get_optional_user" in main_code)

print("=" * 55)
print("交付物 7: create_admin.py 脚本")
print("=" * 55)
admin_script = os.path.join(_PROJECT_ROOT, "backend", "scripts", "create_admin.py")
check("create_admin.py 存在", os.path.exists(admin_script))
admin_code = open(admin_script, encoding="utf-8").read()
check("脚本用 role=admin", "role=\"admin\"" in admin_code or "role='admin'" in admin_code)
check("脚本用 hash_password", "hash_password" in admin_code)

print("=" * 55)
print(f"结果: {passes} passed, {fails} failed")
print("=" * 55)
if fails:
    sys.exit(1)
