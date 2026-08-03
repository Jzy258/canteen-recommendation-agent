"""
天气推荐工具（A 拥有）

按天气类型推荐菜品：天冷 → 热汤面/炖菜/热饮，天热 → 凉菜/清淡/水果。
映射配置在 backend/data/weather_food_map.csv，查询函数 db.get_dishes_by_weather_tag。
"""
from langchain_core.tools import tool


@tool
def recommend_by_weather(weather_type: str, top_k: int = 5) -> list[dict]:
    """按天气推荐菜品。
    Args:
        weather_type: 天气类型，cold=天冷(热汤面/炖菜/热饮) 或 hot=天热(凉菜/清淡/水果)
        top_k: 返回数量，默认 5
    Returns:
        推荐的菜品列表（含营养信息）。
    """
    from db import get_db
    return get_db().get_dishes_by_weather_tag(weather_type)[:top_k]