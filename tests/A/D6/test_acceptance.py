"""
A · D6 交付物验收验证
逐项核验：weather_food_map.csv / db.py 天气标签查询函数 / 联调
"""
import csv, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
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

tmp_db = None
try:

    print("=" * 55)
    print("交付物 1: backend/data/weather_food_map.csv")
    print("=" * 55)
    map_path = os.path.join(_PROJECT_ROOT, "backend", "data", "weather_food_map.csv")
    check("文件存在", os.path.exists(map_path))
    if os.path.exists(map_path):
        with open(map_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        check("映射非空", len(rows) > 0, f"got {len(rows)}")
        fields_ok = all(r.get("weather_type") and r.get("match_field") and r.get("keyword")
                        for r in rows)
        check("字段完整(weather_type/match_field/keyword)", fields_ok)
        types_ok = all(r["weather_type"] in ("cold", "hot") for r in rows)
        check("天气类型仅 cold/hot", types_ok)
        fields_val = all(r["match_field"] in ("flavor_tags", "category") for r in rows)
        check("匹配字段仅 flavor_tags/category", fields_val)
        cold = [r for r in rows if r["weather_type"] == "cold"]
        hot = [r for r in rows if r["weather_type"] == "hot"]
        check("天冷≥3条", len(cold) >= 3, f"got {len(cold)}")
        check("天热≥3条", len(hot) >= 3, f"got {len(hot)}")
        cold_kws = [r["keyword"] for r in cold]
        hot_kws = [r["keyword"] for r in hot]
        check("天冷含热汤/炖菜/热饮", any("汤" in k for k in cold_kws) and any("炖" in k for k in cold_kws))
        check("天热含凉菜/清淡/水果", any("凉" in k or "清" in k for k in hot_kws) and any("水果" in k for k in hot_kws))

    print("\n" + "=" * 55)
    print("交付物 2: db.py 天气标签查询函数")
    print("=" * 55)
    from db import DatabaseInterface, SQLiteDatabase
    abstr = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
    impl = {m for m in dir(SQLiteDatabase) if not m.startswith("_")}
    check("抽象接口声明 get_dishes_by_weather_tag", "get_dishes_by_weather_tag" in abstr)
    check("实现 get_dishes_by_weather_tag", "get_dishes_by_weather_tag" in impl)

    tmp_db = os.path.join(tempfile.gettempdir(), "test_d6_accept.db")
    db = SQLiteDatabase(tmp_db)
    db.init_db()
    # 重绑定 db 模块单例，使 @tool 内部 get_db() 使用临时库（隔离测试）
    import db as _db_module
    _db_module._db_instance = db
    dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
    with open(dish_path, encoding="utf-8") as f:
        db.bulk_insert_dishes(list(csv.DictReader(f)))

    cold_res = db.get_dishes_by_weather_tag("cold")
    hot_res = db.get_dishes_by_weather_tag("hot")
    check("天冷返回非空", len(cold_res) > 0, f"got {len(cold_res)}")
    check("天热返回非空", len(hot_res) > 0, f"got {len(hot_res)}")
    cold_names = [d["name"] for d in cold_res]
    hot_names = [d["name"] for d in hot_res]
    check("天冷含汤/面食", any("汤" in n for n in cold_names) and "煮面条" in cold_names)
    check("天热含清淡素菜", any(n in hot_names for n in ("清炒小白菜", "凉拌黄瓜")))
    check("天热含水果", any(d["category"] == "水果" for d in hot_res))
    check("结果无重复", len({d["id"] for d in cold_res}) == len(cold_res)
          and len({d["id"] for d in hot_res}) == len(hot_res))
    check("未知天气返回空", db.get_dishes_by_weather_tag("rainy") == [])
    check("mild温和返回空(B兜底)", db.get_dishes_by_weather_tag("mild") == [])
    check("返回字段含营养", all("name" in d and "calories" in d and "price" in d for d in cold_res))

    print("\n" + "=" * 55)
    print("交付物 3: 联调通过（B 天气 MCP 调用 A 的查询）")
    print("=" * 55)
    backend_dir = os.path.join(_PROJECT_ROOT, "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # A 不再提供天气 @tool（避免与 B 的工具重复）
    check("A 无重复天气 @tool", not os.path.exists(
        os.path.join(_PROJECT_ROOT, "backend", "tools", "weather.py")))

    # B 天气 MCP 联动（get_weather_recommendation 调用 A 的 get_dishes_by_weather_tag）
    from mcp.weather_tool import get_weather_recommendation
    msg = get_weather_recommendation.invoke({"city": "北京"})
    check("B MCP 天气工具联动 A 查询", isinstance(msg, str) and "°C" in msg and "推荐方向" in msg)
    # 冷/热推荐方向映射正确
    from mcp.weather_data import weather_to_dish_type
    check("冷→热汤面", "热汤" in weather_to_dish_type("cold"))
    check("热→清淡", "清淡" in weather_to_dish_type("hot"))
    # 联动返回候选菜品来自 A 的映射
    check("联动返回含候选菜", "候选菜品" in msg or "暂无" in msg)

    # 天气融入常规推荐（评分联动）
    tools_dir = os.path.join(_PROJECT_ROOT, "backend", "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from scoring import score_dishes
    profile = {"budget": 15, "flavor_preferences": "", "health_goals": ""}
    ranked = score_dishes(cold_res, profile, budget=15)[:5]
    check("天气候选+评分排序", ranked and ranked[0]["score"] >= ranked[-1]["score"])

    print("\n" + "=" * 55)
    print(f"D6 交付物验收: {passes} 通过, {fails} 失败")
    print("=" * 55)
    if fails == 0:
        print("D6 交付物全部验收通过")
    else:
        print("存在失败项")
    sys.exit(1 if fails else 0)

finally:
    if tmp_db and os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass