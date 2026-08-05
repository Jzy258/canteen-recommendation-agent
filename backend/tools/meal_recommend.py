"""按餐次推荐（B 拥有 · 自动根据当前时间推荐早/午/晚餐）

流程：
1. 根据当前本地时间判定餐次（breakfast/lunch/dinner/snack）
2. 优先取「当天该餐次的菜单」菜品（get_dishes_for_menu）
3. 若无当日菜单，回退用全部菜品
4. 用 A 的评分公式（tools.scoring）对候选菜品打分
5. 返回推荐结果 + 餐次标签
"""
from datetime import date

from langchain_core.tools import tool
from tools.meal_time import current_meal, meal_label, current_meal_label


@tool
def recommend_for_meal(budget: float = 20, preferences: str = "",
                       health_goals: str = "", top_k: int = 5) -> dict:
    """根据当前时间自动推荐当前餐次（早/午/晚餐）的菜品。
    适合用户问"现在吃什么"、"推荐一餐"等。
    Args:
        budget: 预算（元/餐），默认 20。
        preferences: 口味偏好，逗号分隔（如 "辣,清淡"）。
        health_goals: 营养目标（高蛋白/控油/控糖/增肌/减脂），可空。
        top_k: 返回数量，默认 5。
    Returns:
        dict: {meal, meal_label, dishes:[...], source}
    """
    from db import get_db
    from tools.scoring import score_dishes

    meal = current_meal()
    label = meal_label(meal)
    db = get_db()

    # 优先取当日该餐次菜单
    today = date.today().isoformat()
    candidates = db.get_dishes_for_menu(today, meal) or []
    source = "当日菜单"
    # 无当日菜单则回退全部菜品（夜宵无菜单，回退全部）
    if not candidates:
        candidates = db.get_all_dishes()
        source = "全部菜品（当日菜单缺失，回退）"

    # 合并用户画像
    saved = db.get_user_profile() or {}
    try:
        budget_f = float(budget)
    except (TypeError, ValueError):
        budget_f = 0
    if not budget_f or budget_f < 0:
        budget_f = float(saved.get("budget") or 20)
    effective_prefs = preferences if preferences else saved.get("flavor_preferences", "")
    effective_goal = health_goals if health_goals else saved.get("health_goals", "")

    if not top_k or top_k < 0:
        top_k = 5

    # 预算硬约束 + 评分
    in_budget = [d for d in candidates if float(d["price"]) <= budget_f]
    user_profile = {
        "budget": budget_f,
        "flavor_preferences": effective_prefs,
        "health_goals": effective_goal,
    }
    scored = score_dishes(in_budget, user_profile, budget=budget_f)
    top = scored[:top_k]

    # 一餐推荐展示前 SHOWN 道，保证话术/返回/总价三者自洽：
    # total_price 必须等于实际展示菜品的价格之和，避免"列出3道却说5道总价"。
    SHOWN = 3
    shown = top[:SHOWN]
    total_price = round(sum(float(d["price"]) for d in shown), 2)

    # 生成可直接展示的推荐话术（确保回复中体现餐次）
    top_names = "、".join(f"{d['name']}({float(d['price']):g}元)" for d in shown)
    if shown:
        suggestion = (f"现在是{label}时间，建议您尝尝：{top_names}。"
                      f"（参考自{source}，预算内，共{total_price:g}元）")
    else:
        suggestion = f"现在是{label}时间，当前预算内暂无合适菜品，建议适当提高预算。"

    return {
        "meal": meal,
        "meal_label": label,
        "dishes": shown,
        "source": source,
        "current_time": date.today().isoformat(),
        "suggestion": suggestion,
        "total_price": total_price,
    }