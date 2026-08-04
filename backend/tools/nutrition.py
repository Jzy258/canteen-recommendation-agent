"""单菜营养成分查询（B 拥有）

按菜名/关键词查询指定菜品的营养成分：
- 精确名称优先，其次关键词模糊匹配
- 返回 calories/protein/carbs/fat/price/category 等字段
"""
from langchain_core.tools import tool


def _format_nutrition(dish: dict) -> dict:
    """从菜品记录提取营养字段。"""
    return {
        "name": dish.get("name"),
        "calories": dish.get("calories"),
        "protein": dish.get("protein"),
        "carbs": dish.get("carbs"),
        "fat": dish.get("fat"),
        "price": dish.get("price"),
        "category": dish.get("category"),
        "flavor_tags": dish.get("flavor_tags"),
        "source": dish.get("source"),
    }


@tool
def get_dish_nutrition(dish_name: str) -> dict:
    """查询指定菜品的营养成分（热量/蛋白质/碳水/脂肪/价格）。
    Args:
        dish_name: 菜品名称，如 "红烧肉"。
    Returns:
        dict: 营养信息；未找到时返回 {"error": ...}。
    """
    from db import get_db

    db = get_db()
    # 精确名称优先
    dish = db.get_dish_by_name(dish_name)
    if dish:
        return _format_nutrition(dish)
    # 关键词模糊匹配
    results = db.search_dishes(keyword=dish_name)
    if results:
        return _format_nutrition(results[0])
    return {"error": f"未找到菜品：{dish_name}"}