from langchain_core.tools import tool


@tool
def search_dish(keyword: str = "") -> list[dict]:
    """Search for dishes by name keyword. Returns matching dishes with nutrition info and price."""
    from db import get_db
    return get_db().search_dishes(keyword=keyword)


@tool
def get_all_dishes() -> list[dict]:
    """Get all available dishes in the canteen."""
    from db import get_db
    return get_db().get_all_dishes()