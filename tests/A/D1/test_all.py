"""
A · D1 阶段全部验证测试
覆盖：schema.sql / dishes.csv / db.py / init_db.py
"""
import csv, json, os, sys, tempfile

# ============================================================
# 1. schema.sql 完整性检查
# ============================================================
print("=" * 50)
print("1. schema.sql 完整性检查")
print("=" * 50)

schema_path = "backend/db/schema.sql"
assert os.path.exists(schema_path), "schema.sql 不存在"
with open(schema_path, encoding="utf-8") as f:
    sql = f.read()

required_tables = ["dish", "menu", "menu_item", "meal_record", "user_profile"]
for t in required_tables:
    assert f"CREATE TABLE IF NOT EXISTS {t}" in sql, f"缺少表 {t}"
    print(f"  [PASS] 表 {t}")

required_views = ["v_menu_detail", "v_daily_nutrition", "v_weekly_nutrition"]
for v in required_views:
    assert f"CREATE VIEW IF NOT EXISTS {v}" in sql, f"缺少视图 {v}"
    print(f"  [PASS] 视图 {v}")

# ============================================================
# 2. dishes.csv 数据完整性检查
# ============================================================
print("\n" + "=" * 50)
print("2. dishes.csv 数据完整性检查")
print("=" * 50)

csv_path = "backend/data/dishes.csv"
with open(csv_path, encoding="utf-8") as f:
    dishes = list(csv.DictReader(f))

assert len(dishes) >= 50, f"菜品数不足50: {len(dishes)}"
print(f"  [PASS] 菜品总数: {len(dishes)}")

required_fields = ["name", "calories", "protein", "carbs", "fat", "price", "category", "flavor_tags", "source"]
numeric_fields = ["calories", "protein", "carbs", "fat", "price"]

cats = {}
for d in dishes:
    c = d["category"]
    cats[c] = cats.get(c, 0) + 1
    for field in required_fields:
        assert field in d and d[field] is not None, f'{d.get("name","?")} 缺少字段 {field}'
    for field in numeric_fields:
        float(d[field])  # 可转为数值

print(f"  [PASS] 字段完整 (共 {len(required_fields)} 个字段)")
print(f"  [PASS] 数值字段可解析")
print(f"  [PASS] 分类分布: {dict(sorted(cats.items()))}")

# 检查重复名称
names = [d["name"] for d in dishes]
assert len(names) == len(set(names)), "存在重复菜品名称"
print("  [PASS] 无重复菜品名称")

# 检查来源标注
for d in dishes:
    assert d["source"].strip(), f'{d["name"]} 未标注参考来源'
print("  [PASS] 全部菜品标注参考来源")

# ============================================================
# 3. db.py 接口完整性检查
# ============================================================
print("\n" + "=" * 50)
print("3. db.py 接口完整性检查")
print("=" * 50)

sys.path.insert(0, "backend/db")
from db import DatabaseInterface, SQLiteDatabase, get_db, init_db

interface_methods = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
impl_methods = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
missing = interface_methods - impl_methods
assert not missing, f"SQLiteDatabase 缺少实现: {missing}"
print(f"  [PASS] 接口数量: {len(interface_methods)}, 全部实现")

# ============================================================
# 4. init_db.py 结构检查
# ============================================================
print("\n" + "=" * 50)
print("4. init_db.py 结构检查")
print("=" * 50)

init_path = "backend/data/init_db.py"
assert os.path.exists(init_path), "init_db.py 不存在"
with open(init_path, encoding="utf-8") as f:
    content = f.read()
assert "init_db()" in content or "create_tables()" in content, "未调用 init_db/create_tables"
assert "dishes.csv" in content, "未引用 dishes.csv"
assert "bulk_insert_dishes" in content, "未调用 bulk_insert_dishes"
print("  [PASS] init_db.py 结构完整")

# ============================================================
# 5. 完整功能测试（临时数据库）
# ============================================================
print("\n" + "=" * 50)
print("5. 完整功能测试（临时数据库）")
print("=" * 50)

tmp_db = os.path.join(tempfile.gettempdir(), "test_canteen_d1.db")
from db import SQLiteDatabase

db = SQLiteDatabase(tmp_db)
db.init_db()

# 读取 schema.sql 验证表已创建
import sqlite3
conn = sqlite3.connect(tmp_db)
tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
views = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()}
conn.close()
for t in required_tables:
    assert t in tables, f"建表失败: {t}"
for v in required_views:
    assert v in views, f"建视图失败: {v}"
print("  [PASS] 5.0 临时数据库建表成功")

# 5.1 导入菜品
with open(csv_path, encoding="utf-8") as f:
    dishes = list(csv.DictReader(f))
db.bulk_insert_dishes(dishes)
all_d = db.get_all_dishes()
assert len(all_d) >= 50, f"导入后数量不足50: {len(all_d)}"
print(f"  [PASS] 5.1 菜品导入: {len(all_d)} 道")

# 5.2 关键词搜索
r = db.search_dishes(keyword="红烧")
assert len(r) >= 1 and r[0]["name"] == "红烧肉"
print("  [PASS] 5.2 关键词搜索: 红烧")

r = db.search_dishes(keyword="不存在的菜")
assert len(r) == 0
print("  [PASS] 5.2 关键词搜索: 无匹配返回空")

# 5.3 分类筛选
r = db.search_dishes(category="荤菜")
assert len(r) == 27
print("  [PASS] 5.3 分类筛选: 荤菜27道")

r = db.search_dishes(category="素菜")
assert len(r) == 21
print("  [PASS] 5.3 分类筛选: 素菜21道")

# 5.4 价格筛选
r = db.search_dishes(max_price=3)
assert len(r) >= 5
assert all(d["price"] <= 3 for d in r)
print("  [PASS] 5.4 价格筛选: <=3元")

# 5.5 组合筛选
r = db.search_dishes(category="汤", max_price=5)
assert len(r) >= 3
print("  [PASS] 5.5 组合筛选: 汤+<=5元")

# 5.6 精确 ID 查询
d = db.get_dish_by_id(1)
assert d and d["name"] == "红烧肉"
print("  [PASS] 5.6 get_dish_by_id(1)")

assert db.get_dish_by_id(9999) is None
print("  [PASS] 5.6 get_dish_by_id(不存在)")

# 5.7 精确名称查询
d = db.get_dish_by_name("麻婆豆腐")
assert d and d["category"] == "素菜"
print("  [PASS] 5.7 get_dish_by_name(麻婆豆腐)")

assert db.get_dish_by_name("不存在的菜") is None
print("  [PASS] 5.7 get_dish_by_name(不存在)")

# 5.8 全部菜品
all_d = db.get_all_dishes()
assert len(all_d) == 100
for d in all_d:
    for k in ["id", "name", "calories", "protein", "carbs", "fat", "price", "category", "source"]:
        assert k in d, f"{d.get('name')} 缺少字段 {k}"
print("  [PASS] 5.8 get_all_dishes: 100道, 字段完整")

# 5.9 用户画像
uid = db.upsert_user_profile(budget=20, flavor_preferences="清淡", dietary_restrictions="海鲜过敏", health_goals="减脂")
assert uid > 0
p = db.get_user_profile()
assert p["budget"] == 20.0
assert p["flavor_preferences"] == "清淡"
assert p["dietary_restrictions"] == "海鲜过敏"
assert p["health_goals"] == "减脂"
print("  [PASS] 5.9 user_profile: 创建")

db.upsert_user_profile(budget=25, flavor_preferences="清淡", health_goals="增肌")
p = db.get_user_profile()
assert p["budget"] == 25.0
assert p["health_goals"] == "增肌"
assert p["flavor_preferences"] == "清淡"
print("  [PASS] 5.9 user_profile: 更新")

db.update_nutrition_summary(json.dumps({"avg_calories": 600, "avg_protein": 25}))
p = db.get_user_profile()
summary = json.loads(p["nutrition_summary"])
assert summary["avg_calories"] == 600
print("  [PASS] 5.9 user_profile: 营养汇总更新")

# 5.10 摄入记录
rid = db.add_meal_record("2026-08-03", "lunch", 1, 1.0)
assert rid > 0
print("  [PASS] 5.10 meal_record: 添加")

pending = db.get_pending_records()
assert len(pending) == 1
assert pending[0]["dish_name"] == "红烧肉"
assert pending[0]["confirmed"] == 0
print("  [PASS] 5.10 meal_record: 待确认查询")

ok = db.confirm_meal_record(rid)
assert ok
records = db.get_records_by_date("2026-08-03")
assert len(records) == 1
assert records[0]["confirmed"] == 1
print("  [PASS] 5.10 meal_record: 确认")

ok = db.reject_meal_record(9999)  # 不存在的记录
assert not ok
print("  [PASS] 5.10 meal_record: 拒绝不存在记录")

# 5.11 营养汇总
daily = db.get_daily_nutrition("2026-08-03")
assert len(daily) == 1
assert daily[0]["total_calories"] == 500.0
assert daily[0]["dish_count"] == 1
print("  [PASS] 5.11 v_daily_nutrition")

weekly = db.get_weekly_nutrition("2026-08-01", "2026-08-07")
assert len(weekly) == 1
print("  [PASS] 5.11 v_weekly_nutrition")

# 5.12 天气推荐
hot = db.get_dishes_by_weather_tag("hot")
assert len(hot) >= 1
cold = db.get_dishes_by_weather_tag("cold")
print(f"  [PASS] 5.12 weather: 天热{len(hot)}道, 天冷{len(cold)}道")

unknown = db.get_dishes_by_weather_tag("unknown")
assert len(unknown) == 0
print("  [PASS] 5.12 weather: 未知天气返回空")

# 5.13 幂等性
db.bulk_insert_dishes(dishes)
assert len(db.get_all_dishes()) == 100
print("  [PASS] 5.13 幂等性: 重复导入0条")

# 5.14 边界条件
r = db.search_dishes(keyword="")
assert len(r) == 100
print("  [PASS] 5.14 边界: 空关键词返回全部")

r = db.search_dishes(keyword="!@#$%")
assert len(r) == 0
print("  [PASS] 5.14 边界: 特殊字符返回空")

r = db.search_dishes(category="不存在")
assert len(r) == 0
print("  [PASS] 5.14 边界: 不存在分类返回空")

# 5.15 菜单查询（空数据）
r = db.get_menu_by_date("2026-08-03")
assert len(r) == 0
r = db.get_dishes_for_menu("2026-08-03", "lunch")
assert len(r) == 0
print("  [PASS] 5.15 菜单查询: 空数据返回空")

# 清理
os.remove(tmp_db)

print("\n" + "=" * 50)
print("全部验证通过")
print("=" * 50)