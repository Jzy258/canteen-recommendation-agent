from langchain_core.tools import tool


@tool
def search_dish(keyword: str = "") -> list[dict]:
    """按菜名关键词搜索菜品，返回匹配菜品的营养信息与价格。"""
    from db import get_db
    return get_db().search_dishes(keyword=keyword)


@tool
def get_all_dishes() -> list[dict]:
    """获取食堂全部可用菜品。"""
    from db import get_db
    return get_db().get_all_dishes()