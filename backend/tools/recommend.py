from langchain_core.tools import tool
from db import get_db

db = get_db()


def _score_dish(dish: dict, budget: float, pref_category: str,
                pref_flavor: str, health_goal: str) -> float:
    score = 50.0

    # Price suitability (0-30 points)
    if budget > 0:
        if dish["price"] <= budget:
            price_ratio = dish["price"] / budget
            if price_ratio <= 0.5:
                score += 30
            elif price_ratio <= 0.8:
                score += 20
            else:
                score += 10
        else:
            score -= 20

    # Category preference (0-20 points)
    if pref_category and dish["category"] == pref_category:
        score += 20
    elif pref_category == "荤菜" and dish["category"] in ("荤菜", "汤"):
        score += 10
    elif pref_category == "素菜" and dish["category"] in ("素菜", "主食"):
        score += 10

    # Flavor preference (0-20 points)
    if pref_flavor and dish["flavor_tags"]:
        dish_flavors = [f.strip() for f in dish["flavor_tags"].split(",")]
        if pref_flavor in dish_flavors:
            score += 20
        elif any(pref_flavor in f for f in dish_flavors):
            score += 10

    # Health goal alignment (0-30 points)
    if health_goal:
        if health_goal == "高蛋白" and dish["protein"] >= 20:
            score += 30
        elif health_goal == "高蛋白" and dish["protein"] >= 15:
            score += 15
        elif health_goal == "控油" and dish["fat"] <= 10:
            score += 30
        elif health_goal == "控油" and dish["fat"] <= 15:
            score += 15
        elif health_goal == "控糖" and dish["carbs"] <= 20:
            score += 30
        elif health_goal == "控糖" and dish["carbs"] <= 30:
            score += 15
        elif health_goal == "低卡" and dish["calories"] <= 200:
            score += 30
        elif health_goal == "低卡" and dish["calories"] <= 300:
            score += 15

    return round(score, 1)


@tool
def recommend_dishes(
    budget: float = 0,
    pref_category: str = "",
    pref_flavor: str = "",
    health_goal: str = "",
    top_n: int = 5,
) -> list[dict]:
    """Recommend dishes based on budget, category preference, flavor preference, and health goal.
    Returns scored dishes sorted by recommendation score descending."""
    dishes = db.get_all_dishes()
    scored = []
    for d in dishes:
        s = _score_dish(d, budget, pref_category, pref_flavor, health_goal)
        scored.append({**d, "recommend_score": s})
    scored.sort(key=lambda x: x["recommend_score"], reverse=True)
    return scored[:top_n]