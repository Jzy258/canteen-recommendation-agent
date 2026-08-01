from langchain_core.tools import tool
from db import get_db

db = get_db()


@tool
def search_dish(keyword: str = "") -> list[dict]:
    """Search for dishes by name keyword. Returns matching dishes with nutrition info and price."""
    return db.search_dishes(keyword=keyword)


@tool
def get_all_dishes() -> list[dict]:
    """Get all available dishes in the canteen."""
    return db.get_all_dishes()