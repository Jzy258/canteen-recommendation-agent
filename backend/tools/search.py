from langchain_core.tools import tool

DISHES = [
    {"name": "红烧肉", "calories": 500, "protein": 18, "carbs": 10, "fat": 35, "price": 12, "category": "荤菜", "tags": ["猪肉", "红烧"]},
    {"name": "宫保鸡丁", "calories": 350, "protein": 22, "carbs": 20, "fat": 18, "price": 10, "category": "荤菜", "tags": ["鸡肉", "辣"]},
    {"name": "番茄炒蛋", "calories": 200, "protein": 10, "carbs": 15, "fat": 12, "price": 8, "category": "素菜", "tags": ["鸡蛋", "番茄"]},
    {"name": "清炒青菜", "calories": 80, "protein": 4, "carbs": 6, "fat": 4, "price": 5, "category": "素菜", "tags": ["青菜", "清淡"]},
    {"name": "麻婆豆腐", "calories": 220, "protein": 12, "carbs": 14, "fat": 14, "price": 7, "category": "素菜", "tags": ["豆腐", "辣", "川菜"]},
    {"name": "糖醋里脊", "calories": 420, "protein": 20, "carbs": 30, "fat": 22, "price": 11, "category": "荤菜", "tags": ["猪肉", "酸甜"]},
    {"name": "土豆烧牛肉", "calories": 380, "protein": 25, "carbs": 28, "fat": 16, "price": 13, "category": "荤菜", "tags": ["牛肉", "土豆"]},
    {"name": "蒜蓉西兰花", "calories": 90, "protein": 5, "carbs": 8, "fat": 3, "price": 6, "category": "素菜", "tags": ["西兰花", "清淡"]},
    {"name": "鱼香肉丝", "calories": 320, "protein": 18, "carbs": 22, "fat": 16, "price": 10, "category": "荤菜", "tags": ["猪肉", "鱼香", "川菜"]},
    {"name": "酸辣土豆丝", "calories": 150, "protein": 3, "carbs": 28, "fat": 5, "price": 6, "category": "素菜", "tags": ["土豆", "酸辣"]},
    {"name": "葱爆羊肉", "calories": 400, "protein": 24, "carbs": 8, "fat": 28, "price": 14, "category": "荤菜", "tags": ["羊肉", "葱香"]},
    {"name": "地三鲜", "calories": 180, "protein": 4, "carbs": 22, "fat": 10, "price": 7, "category": "素菜", "tags": ["茄子", "土豆", "青椒"]},
    {"name": "清蒸鲈鱼", "calories": 250, "protein": 30, "carbs": 2, "fat": 12, "price": 15, "category": "荤菜", "tags": ["鱼", "清蒸", "清淡"]},
    {"name": "可乐鸡翅", "calories": 380, "protein": 20, "carbs": 25, "fat": 20, "price": 12, "category": "荤菜", "tags": ["鸡肉", "可乐", "甜"]},
    {"name": "干煸四季豆", "calories": 160, "protein": 5, "carbs": 14, "fat": 10, "price": 7, "category": "素菜", "tags": ["四季豆", "微辣"]},
    {"name": "回锅肉", "calories": 450, "protein": 16, "carbs": 12, "fat": 32, "price": 11, "category": "荤菜", "tags": ["猪肉", "川菜", "辣"]},
    {"name": "西红柿牛腩", "calories": 340, "protein": 22, "carbs": 18, "fat": 18, "price": 14, "category": "荤菜", "tags": ["牛肉", "西红柿", "酸甜"]},
    {"name": "凉拌黄瓜", "calories": 50, "protein": 2, "carbs": 6, "fat": 2, "price": 4, "category": "素菜", "tags": ["黄瓜", "凉拌", "清淡"]},
    {"name": "水煮鱼", "calories": 380, "protein": 28, "carbs": 6, "fat": 26, "price": 16, "category": "荤菜", "tags": ["鱼", "辣", "川菜"]},
    {"name": "蛋炒饭", "calories": 350, "protein": 10, "carbs": 45, "fat": 12, "price": 8, "category": "主食", "tags": ["鸡蛋", "米饭"]},
    {"name": "米饭", "calories": 200, "protein": 4, "carbs": 45, "fat": 0.5, "price": 2, "category": "主食", "tags": ["米饭"]},
    {"name": "馒头", "calories": 180, "protein": 5, "carbs": 38, "fat": 1, "price": 1, "category": "主食", "tags": ["面食"]},
    {"name": "紫菜蛋花汤", "calories": 60, "protein": 4, "carbs": 5, "fat": 2, "price": 3, "category": "汤品", "tags": ["紫菜", "鸡蛋", "清淡"]},
    {"name": "冬瓜排骨汤", "calories": 180, "protein": 14, "carbs": 6, "fat": 12, "price": 8, "category": "汤品", "tags": ["排骨", "冬瓜"]},
    {"name": "红烧茄子", "calories": 200, "protein": 4, "carbs": 18, "fat": 14, "price": 7, "category": "素菜", "tags": ["茄子", "红烧"]},
    {"name": "青椒肉丝", "calories": 280, "protein": 16, "carbs": 12, "fat": 18, "price": 9, "category": "荤菜", "tags": ["猪肉", "青椒"]},
    {"name": "炒豆芽", "calories": 60, "protein": 3, "carbs": 6, "fat": 2, "price": 4, "category": "素菜", "tags": ["豆芽", "清淡"]},
    {"name": "饺子（猪肉白菜）", "calories": 300, "protein": 12, "carbs": 35, "fat": 12, "price": 10, "category": "主食", "tags": ["猪肉", "白菜", "面食"]},
    {"name": "麻辣香锅", "calories": 500, "protein": 22, "carbs": 20, "fat": 35, "price": 15, "category": "荤菜", "tags": ["辣", "川菜", "综合"]},
    {"name": "玉米排骨汤", "calories": 200, "protein": 15, "carbs": 18, "fat": 8, "price": 9, "category": "汤品", "tags": ["排骨", "玉米", "清淡"]},
]


@tool
def search_dish(keyword: str) -> list[dict]:
    """Search for dishes by name or keyword. Returns matching dishes with nutrition info and price."""
    keyword_lower = keyword.lower()
    results = []
    for dish in DISHES:
        if keyword_lower in dish["name"].lower() or keyword_lower in dish["name"]:
            results.append(dish)
            continue
        for tag in dish["tags"]:
            if keyword_lower in tag.lower():
                results.append(dish)
                break
        if keyword_lower in dish["category"]:
            results.append(dish)
    return results[:10]


@tool
def get_all_dishes() -> list[dict]:
    """Get all available dishes in the canteen."""
    return DISHES