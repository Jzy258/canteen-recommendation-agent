"""
A · D9 克重调控交付物验证
覆盖：dish.serving_grams / meal_record.grams / 克重营养换算 / NULL 回退 portion / v1.2 迁移幂等
"""
import csv
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
print("交付物 1: schema.sql v1.2（serving_grams / grams）")
print("=" * 55)
schema = open(os.path.join(_PROJECT_ROOT, "backend", "db", "schema.sql"),
              encoding="utf-8").read()
check("schema 含 serving_grams", "serving_grams" in schema)
check("dish 含标准份量克数", "标准份量克数" in schema or "serving_grams" in schema)
check("meal_record 含 grams", "grams" in schema)
check("视图含克重换算", "mr.grams / d.serving_grams" in schema)

print("=" * 55)
print("交付物 2: dishes.csv 含 serving_grams")
print("=" * 55)
rows = list(csv.DictReader(open(os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv"),
                                encoding="utf-8")))
check("dishes.csv 有 serving_grams 列", "serving_grams" in rows[0])
check("全部 100 道菜都有克重", all(r.get("serving_grams") for r in rows) and len(rows) == 100)
rice = next(r for r in rows if r["name"] == "米饭")
check("米饭 serving_grams=175", rice["serving_grams"] == "175")

print("=" * 55)
print("交付物 3: db.py 克重接口")
print("=" * 55)
db_code = open(os.path.join(_PROJECT_ROOT, "backend", "db", "db.py"),
               encoding="utf-8").read()
for m in ["_serving_factor_sql", "_migrate_v12", "def add_meal_record", "grams"]:
    check(f"db.py 含 {m}", m in db_code)

from db import SQLiteDatabase, DatabaseInterface
impl = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
abstr = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
check("接口抽象与实现一致", abstr.issubset(impl))

print("=" * 55)
print("交付物 4: 克重营养换算")
print("=" * 55)
tmp_db = os.path.join(tempfile.gettempdir(), "test_d9.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
db = SQLiteDatabase(tmp_db)
db.bulk_insert_dishes([
    {"name": "红烧肉", "calories": 500, "protein": 20, "carbs": 10, "fat": 35,
     "price": 12, "category": "荤菜", "flavor_tags": "咸", "source": "t",
     "serving_grams": 150},
    {"name": "米饭", "calories": 200, "protein": 4, "carbs": 45, "fat": 0.5,
     "price": 1, "category": "主食", "flavor_tags": "", "source": "t",
     "serving_grams": 175},
])
# grams 记录：红烧肉 100g → 系数 100/150=0.667
rid = db.add_meal_record("2026-08-04", "lunch", 1, portion=1.0, grams=100)
db.confirm_meal_record(rid)
rec = db.get_records_in_range("2026-08-01", "2026-08-05")[0]
check("grams 记录含实际摄入热量", abs(rec["intake_calories"] - 333.3) < 1,
      rec.get("intake_calories"))
check("记录含 serving_grams", rec.get("serving_grams") == 150)
check("记录含 grams", rec.get("grams") == 100)
day = db.get_day_total("2026-08-04")
check("日合计按克重折算", abs(day["total_calories"] - 333.3) < 1, day)
daily = db.get_daily_nutrition("2026-08-04")
check("餐次营养按克重折算", abs(daily[0]["total_calories"] - 333.3) < 1)
wk = db.get_weekly_summary("2026-08-01", "2026-08-05")
check("周汇总按克重折算", abs(wk["total_calories"] - 333.3) < 1, wk)

# 汇总（user_id 分支也按克重）
uid = db.create_user("alice", "hash", role="user")
db.add_meal_record("2026-08-04", "dinner", 1, portion=1.0, grams=150, user_id=uid)
db.confirm_records([p["id"] for p in db.get_pending_records() if p.get("user_id") == uid])
day_u = db.get_day_total("2026-08-04", user_id=uid)
check("user_id 分支日合计按克重", abs(day_u["total_calories"] - 500.0) < 1, day_u)

print("=" * 55)
print("交付物 5: NULL grams 回退 portion（兼容）")
print("=" * 55)
rid2 = db.add_meal_record("2026-08-05", "lunch", 1, portion=1.0)  # 无 grams
db.confirm_meal_record(rid2)
rec2 = db.get_records_in_range("2026-08-05", "2026-08-05")[0]
check("无 grams 记录 intake = 一份热量", abs(rec2["intake_calories"] - 500.0) < 1,
      rec2.get("intake_calories"))
day2 = db.get_day_total("2026-08-05")
check("NULL 回退 portion 合计", abs(day2["total_calories"] - 500.0) < 1, day2)
# portion=2 无 grams
rid3 = db.add_meal_record("2026-08-05", "dinner", 1, portion=2.0)
db.confirm_meal_record(rid3)
rec3 = db.get_records_in_range("2026-08-05", "2026-08-05")
p2 = [r for r in rec3 if r["dish_id"] == 1 and r["grams"] is None][0]
check("portion=2 无 grams → 2 份热量", abs(p2["intake_calories"] - 1000.0) < 1)

print("=" * 55)
print("交付物 6: v1.2 迁移幂等（v1.1 老库 → v1.2）")
print("=" * 55)
old_db = os.path.join(tempfile.gettempdir(), "test_d9_old.db")
if os.path.exists(old_db):
    os.remove(old_db)
con = sqlite3.connect(old_db)
con.executescript("""
    CREATE TABLE dish (id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE, calories REAL NOT NULL, protein REAL NOT NULL,
        carbs REAL NOT NULL, fat REAL NOT NULL, price REAL NOT NULL,
        category TEXT NOT NULL, flavor_tags TEXT DEFAULT '', source TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')));
    CREATE TABLE meal_record (id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, meal_time TEXT, dish_id INTEGER, portion REAL DEFAULT 1.0,
        confirmed INTEGER DEFAULT 0, user_id INTEGER, created_at TEXT);
""")
con.execute("INSERT INTO dish (name, calories, protein, carbs, fat, price, category, source) VALUES ('饭',200,4,45,0.5,1,'主食','t')")
con.execute("INSERT INTO meal_record (date, meal_time, dish_id, portion, confirmed) VALUES ('2026-08-01','lunch',1,1.0,1)")
con.commit()
con.close()
# 实例化触发 v1.1 + v1.2 迁移
db_old = SQLiteDatabase(old_db)
con = sqlite3.connect(old_db)
dish_cols = [r[1] for r in con.execute("PRAGMA table_info(dish)")]
mr_cols = [r[1] for r in con.execute("PRAGMA table_info(meal_record)")]
check("旧 dish 加 serving_grams", "serving_grams" in dish_cols)
check("旧 meal_record 加 grams", "grams" in mr_cols)
views = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
check("迁移后建聚合视图", "v_day_total" in views)
# 幂等：再次实例化
db_old2 = SQLiteDatabase(old_db)
con2 = sqlite3.connect(old_db)
check("重复迁移幂等（列不重复）",
      len([c for c in [r[1] for r in con2.execute("PRAGMA table_info(dish)")] if c == "serving_grams"]) == 1)
con.close(); con2.close()

print("=" * 55)
print(f"结果: {passes} passed, {fails} failed")
print("=" * 55)
if fails:
    sys.exit(1)
