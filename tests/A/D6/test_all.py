"""
A · D6 天气-菜品标签映射验证
覆盖：weather_food_map.csv 格式 / get_dishes_by_weather_tag 天冷/天热推荐
"""
import csv, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))

tmp_db = None

try:

    print("=" * 50)
    print("1. weather_food_map.csv 格式检查")
    print("=" * 50)
    map_path = os.path.join(_PROJECT_ROOT, "backend", "data", "weather_food_map.csv")
    assert os.path.exists(map_path), "weather_food_map.csv 不存在"
    with open(map_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, "映射文件为空"
    for r in rows:
        assert "weather_type" in r and "match_field" in r and "keyword" in r, f"字段缺失: {r}"
        assert r["weather_type"] in ("cold", "hot"), f"天气类型非法: {r['weather_type']}"
        assert r["match_field"] in ("flavor_tags", "category"), f"匹配字段非法: {r['match_field']}"
        assert r["keyword"].strip(), f"keyword 为空: {r}"
    cold = [r for r in rows if r["weather_type"] == "cold"]
    hot = [r for r in rows if r["weather_type"] == "hot"]
    assert len(cold) >= 3 and len(hot) >= 3, "天冷/天热至少各3条映射"
    print(f"  [PASS] 映射共 {len(rows)} 条 (cold={len(cold)}, hot={len(hot)})")
    print(f"  [PASS] 字段完整, 天气类型/匹配字段合法")
    # 冷天包含热汤面/炖菜类关键词
    cold_kws = "|".join(r["keyword"] for r in cold)
    assert any(k in cold_kws for k in ("汤", "炖")), "冷天应含汤/炖类关键词"
    hot_kws = "|".join(r["keyword"] for r in hot)
    assert any(k in hot_kws for k in ("凉", "清淡", "水果")), "热天应含凉/清淡/水果关键词"
    print("  [PASS] 天冷→热汤/炖菜, 天热→凉菜/清淡/水果")

    # ============================================================
    print("\n" + "=" * 50)
    print("2. get_dishes_by_weather_tag 功能验证（临时库）")
    print("=" * 50)
    tmp_db = os.path.join(tempfile.gettempdir(), "test_d6_weather.db")
    from db import SQLiteDatabase
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
    print(f"  天冷推荐 {len(cold_res)} 道, 天热推荐 {len(hot_res)} 道")
    print(f"  天冷: {[d['name'] for d in cold_res]}")
    print(f"  天热: {[d['name'] for d in hot_res]}")

    # 天冷应包含汤/主食（热汤面类）
    cold_names = [d["name"] for d in cold_res]
    assert any("汤" in n for n in cold_names), f"天冷应含汤: {cold_names}"
    assert "煮面条" in cold_names, "天冷应含面食"
    # 天热应包含清淡素菜/水果
    hot_names = [d["name"] for d in hot_res]
    assert "清炒小白菜" in hot_names or "凉拌黄瓜" in hot_names, f"天热应含清淡素菜: {hot_names}"
    assert any(d["category"] == "水果" for d in hot_res), "天热应含水果"
    print("  [PASS] 天冷含热汤/面食, 天热含清淡素菜/水果")

    # 结果无重复
    assert len({d["id"] for d in cold_res}) == len(cold_res), "天冷结果有重复"
    assert len({d["id"] for d in hot_res}) == len(hot_res), "天热结果有重复"
    print("  [PASS] 结果无重复")

    # 未知天气返回空
    assert db.get_dishes_by_weather_tag("rainy") == []
    print("  [PASS] 未知天气返回空列表")

    # ============================================================
    print("\n" + "=" * 50)
    print("3. 与评分推荐联动（天气融入常规推荐）")
    print("=" * 50)
    # 天冷场景下，推荐应从冷天候选集中按评分取 Top
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "tools"))
    from scoring import score_dishes
    profile = {"budget": 15, "flavor_preferences": "", "health_goals": ""}
    top_cold = score_dishes(cold_res, profile, budget=15)[:5]
    assert top_cold and top_cold[0]["score"] >= top_cold[-1]["score"]
    print(f"  [PASS] 天冷候选中评分 Top3: {[d['name'] for d in top_cold[:3]]}")

    # ============================================================
    print("\n" + "=" * 50)
    print("4. 抽象接口声明")
    print("=" * 50)
    from db import DatabaseInterface
    interface_methods = {m for m in dir(DatabaseInterface) if not m.startswith("_")}
    impl_methods = {m for m in dir(type(db)) if not m.startswith("_")}
    assert "get_dishes_by_weather_tag" in interface_methods, "抽象接口缺天气查询函数"
    assert "get_dishes_by_weather_tag" in impl_methods, "实现缺天气查询函数"
    print("  [PASS] get_dishes_by_weather_tag 已声明于抽象接口并实现")
    # 天气推荐 @tool 由 B 的 get_weather_recommendation 承担，A 不重复提供
    import os.path as _osp
    assert not _osp.exists(_osp.join(_PROJECT_ROOT, "backend", "tools", "weather.py")), \
        "backend/tools/weather.py 应已移除（避免与 B 的天气工具重复）"
    print("  [PASS] A 不再提供天气 @tool（B 的 get_weather_recommendation 承担，工具唯一）")

    # ============================================================
    print("\n" + "=" * 50)
    print("5. 与 B 天气 MCP 联调（get_weather_recommendation 调用 A 的查询）")
    print("=" * 50)
    # B 的天气类型含 mild（温和），A 的映射仅 cold/hot；mild 返回空由 B 兜底
    assert db.get_dishes_by_weather_tag("mild") == []
    print("  [PASS] mild(温和) 返回空列表（由 B 的天气工具走 get_all_dishes 兜底）")

    # B 的 weather_tool 直接调用 db.get_dishes_by_weather_tag（需 backend 在 sys.path）
    backend_dir = os.path.join(_PROJECT_ROOT, "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from mcp.weather_tool import get_weather_recommendation
    msg = get_weather_recommendation.invoke({"city": "北京"})
    assert isinstance(msg, str) and "°C" in msg, f"返回应为天气描述: {msg}"
    assert "推荐方向" in msg or "候选菜品" in msg, f"应含推荐方向/候选菜: {msg}"
    print(f"  [PASS] get_weather_recommendation 联动成功: {msg[:60]}...")
    # 冷天推荐方向命中热汤面
    from mcp.weather_data import weather_to_dish_type
    assert "热汤" in weather_to_dish_type("cold"), "cold 应映射热汤面"
    assert "清淡" in weather_to_dish_type("hot"), "hot 应映射清淡"
    print("  [PASS] weather_to_dish_type 冷→热汤面/热→清淡")

    # 天气候选与 A 的评分排序一致（天气推荐可叠加评分）
    import json
    wdata = __import__("mcp.weather_data", fromlist=["get_weather", "weather_to_dish_type"])
    weather = wdata.get_weather("北京")
    assert weather["weather_type"] in ("cold", "hot", "mild"), f"天气类型异常: {weather}"
    direction = wdata.weather_to_dish_type(weather["weather_type"])
    assert direction, "推荐方向非空"
    print(f"  [PASS] 天气数据源: {weather['city']} {weather['temperature']}°C "
          f"type={weather['weather_type']} source={weather['source']}")
    print(f"  [PASS] 推荐方向映射: {direction}")

    print("\n" + "=" * 50)
    print("全部验证通过")
    print("=" * 50)

finally:
    if tmp_db and os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass