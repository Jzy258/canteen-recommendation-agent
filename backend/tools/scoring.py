"""
推荐评分公式（A 拥有 · 自研核心）

评分公式：Score = W_budget·S_budget + W_nutrition·S_nutrition + W_pref·S_pref

- W_budget    = 0.35  预算约束（价格 ≤ 预算）
- W_nutrition = 0.40  营养均衡（热量/蛋白质/碳水/脂肪 相对目标值的偏离度）
- W_pref      = 0.25  偏好权重（口味标签 + 荤素类别）

系数与目标值详见 docs/评分公式说明.md，本文件为唯一实现。
"""
from typing import Optional

# =============================================================================
# 系数（与 docs/评分公式说明.md 保持一致）
# =============================================================================

WEIGHTS = {
    "budget": 0.35,      # 预算约束权重
    "nutrition": 0.40,   # 营养均衡权重
    "preference": 0.25,  # 偏好权重
}

PREF_WEIGHTS = {
    "flavor": 0.6,   # 口味标签匹配权重
    "category": 0.4, # 荤素类别偏好权重
}

# 各类别的营养目标值（一份食堂份量）
CATEGORY_TARGETS = {
    "荤菜": {"calories": 350, "protein": 22, "carbs": 15, "fat": 20},
    "素菜": {"calories": 120, "protein": 8,  "carbs": 12, "fat": 6},
    "汤":   {"calories": 90,  "protein": 8,  "carbs": 8,  "fat": 5},
    "主食": {"calories": 250, "protein": 6,  "carbs": 45, "fat": 2},
    "水果": {"calories": 80,  "protein": 1,  "carbs": 20, "fat": 0.3},
    "饮品": {"calories": 80,  "protein": 3,  "carbs": 12, "fat": 2},
}

# 营养目标权重（按 health_goals 调整各营养指标的重要性）
GOAL_NUTRITION_WEIGHTS = {
    "":       {"calories": 0.25, "protein": 0.25, "carbs": 0.25, "fat": 0.25},
    "高蛋白": {"calories": 0.15, "protein": 0.50, "carbs": 0.15, "fat": 0.20},
    "增肌":   {"calories": 0.15, "protein": 0.55, "carbs": 0.15, "fat": 0.15},
    "控油":   {"calories": 0.20, "protein": 0.20, "carbs": 0.15, "fat": 0.45},
    "控糖":   {"calories": 0.20, "protein": 0.20, "carbs": 0.45, "fat": 0.15},
    "减脂":   {"calories": 0.35, "protein": 0.25, "carbs": 0.15, "fat": 0.25},
}

NUTRIENTS = ["calories", "protein", "carbs", "fat"]

# 减脂/控油目标偏好素菜
LEAN_PREFER_VEGETARIAN = {"减脂", "控油"}


# =============================================================================
# 评分函数
# =============================================================================

def budget_score(price: float, budget: float) -> float:
    """预算约束得分 [0,1]：价格 ≤ 预算得 1；超预算线性衰减。
    异常输入（None/非数值）返回中性 1.0。"""
    try:
        price = float(price)
        budget = float(budget)
    except (TypeError, ValueError):
        return 1.0
    if budget <= 0:
        return 1.0
    if price <= budget:
        return 1.0
    # 超出部分按 2 倍预算为界线性降到 0
    exceed = (price - budget) / max(budget, 0.01)
    return max(0.0, 1.0 - exceed / 2.0)


def nutrition_score(dish: dict, health_goal: str = "") -> float:
    """营养均衡得分 [0,1]：各项营养相对类别目标的偏离度越小得分越高。
    dish 为 None 或空时返回中性 0。"""
    if not dish:
        return 0.0
    category = dish.get("category") or "素菜"
    targets = CATEGORY_TARGETS.get(category, CATEGORY_TARGETS["素菜"])
    goal_weights = GOAL_NUTRITION_WEIGHTS.get(health_goal, GOAL_NUTRITION_WEIGHTS[""])

    deviation_sum = 0.0
    for n in NUTRIENTS:
        try:
            actual = float(dish.get(n, 0))
        except (TypeError, ValueError):
            actual = 0.0
        target = targets[n]
        # 相对偏离度，封顶 1.0
        dev = min(abs(actual - target) / max(target, 0.01), 1.0)
        deviation_sum += goal_weights[n] * dev
    return max(0.0, 1.0 - deviation_sum)


def preference_score(dish: dict, user_profile: dict) -> float:
    """偏好得分 [0,1]：口味标签匹配 + 荤素类别偏好。
    dish/user_profile 为 None 时返回中性 0.5。"""
    if not dish or not user_profile:
        return 0.5
    pref_flavors = _split(user_profile.get("flavor_preferences", ""))
    dish_flavors = _split(dish.get("flavor_tags", ""))
    health_goal = user_profile.get("health_goals", "")
    category = dish.get("category", "")

    # 口味匹配：用户偏好的口味中，命中菜品标签的比例（无偏好取中性 0.5）
    if pref_flavors:
        flavor_score = sum(1 for f in pref_flavors if f in dish_flavors) / len(pref_flavors)
    else:
        flavor_score = 0.5

    # 荤素偏好：减脂/控油偏好素菜；否则中性 0.5
    if health_goal in LEAN_PREFER_VEGETARIAN:
        category_score = 1.0 if category == "素菜" else 0.3
    else:
        category_score = 0.5

    return PREF_WEIGHTS["flavor"] * flavor_score + PREF_WEIGHTS["category"] * category_score


def score_dish(dish: dict, user_profile: dict, budget: Optional[float] = None) -> dict:
    """对单个菜品评分，返回总分与分项得分（供生成推荐理由）。
    dish 为 None 时返回零分结果。"""
    dish = dish or {}
    user_profile = user_profile or {}
    budget = budget if budget is not None else float(user_profile.get("budget", 0) or 0)

    s_budget = budget_score(float(dish.get("price", 0)), budget)
    s_nutrition = nutrition_score(dish, user_profile.get("health_goals", ""))
    s_pref = preference_score(dish, user_profile)

    total = (
        WEIGHTS["budget"] * s_budget
        + WEIGHTS["nutrition"] * s_nutrition
        + WEIGHTS["preference"] * s_pref
    )

    return {
        "score": round(total, 4),
        "budget_score": round(s_budget, 4),
        "nutrition_score": round(s_nutrition, 4),
        "preference_score": round(s_pref, 4),
        "price": float(dish.get("price", 0)),
        "budget": float(budget),
    }


def score_dishes(dishes: list[dict], user_profile: dict,
                 budget: Optional[float] = None) -> list[dict]:
    """批量评分并排序（从高到低），每项附 score 明细。
    dishes 为 None 时返回空列表。"""
    dishes = dishes or []
    scored = []
    for d in dishes:
        s = score_dish(d, user_profile, budget)
        item = dict(d or {})
        item["score"] = s["score"]
        item["budget_score"] = s["budget_score"]
        item["nutrition_score"] = s["nutrition_score"]
        item["preference_score"] = s["preference_score"]
        scored.append(item)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def _split(text: str) -> list[str]:
    """按逗号拆分去空格。"""
    return [t.strip() for t in str(text).split(",") if t.strip()]


# =============================================================================
# 忌口过滤（启发式）
# 菜品暂无配料/过敏原字段，故基于「菜名 + 口味标签 + 类别」做启发式匹配，
# 命中即视为忌口并剔除。后续给 dishes 增加配料列后可升级为精确过滤。
# =============================================================================


def _is_restricted(dish: dict, restriction: str) -> bool:
    """判断一道菜是否命中一条忌口。

    规则：
    - 素食/不吃肉 → 排除类别为「荤菜」
    - 清真/不吃猪肉/猪肉 → 排除菜名含"猪"，或含"肉"但非牛羊鱼鸡鸭虾兔
    - 口味类（辣/麻辣/酸辣）→ 排除 flavor_tags 命中
    - 其他关键词（如 香菜/花生/茄子）→ 菜名或 flavor_tags 命中
    """
    if not dish or not restriction:
        return False
    name = str(dish.get("name", ""))
    tags = _split(dish.get("flavor_tags", ""))
    category = str(dish.get("category", ""))
    r = str(restriction).strip()

    if r in ("素食", "吃素", "不吃肉"):
        return category == "荤菜"
    if r in ("清真", "不吃猪肉", "猪肉"):
        non_pork = ("牛", "羊", "鸡", "鸭", "虾", "兔", "驴")
        if "猪" in name:
            return True
        # "鱼香肉丝" 是猪肉菜（"鱼香"为调味词，非食材）
        if "鱼香" in name and "肉" in name:
            return True
        return ("肉" in name) and not any(k in name for k in non_pork)

    kw = (r.replace("不吃", "").replace("不能吃", "").replace("忌", "")
          .replace("过敏", "").replace("忌口", "").strip())
    if not kw:
        return False
    if kw in ("辣", "麻辣", "酸辣"):
        return any(kw in t for t in tags)
    if kw in name:
        return True
    return any(kw in t for t in tags)


def filter_by_restrictions(dishes: list[dict], restrictions: str = "") -> list[dict]:
    """按忌口列表（逗号分隔）剔除命中忌口的菜品。dishes 为 None 时返回空列表。"""
    dishes = dishes or []
    items = _split(restrictions)
    if not items:
        return dishes
    return [d for d in dishes if not any(_is_restricted(d, r) for r in items)]


# =============================================================================
# @tool：推荐接口（B 的 agent 可注册调用）
# =============================================================================

from langchain_core.tools import tool


@tool
def recommend(budget: float = 20, preferences: str = "",
              health_goals: str = "", dietary_restrictions: str = "",
              top_k: int = 5) -> list[dict]:
    """推荐符合预算与营养需求的菜品。
    Args:
        budget: 预算（元/餐），默认 20；不传或为 0 时使用已保存的用户画像。
        preferences: 口味偏好，逗号分隔（如 "辣,清淡"）；为空时使用已保存画像。
        health_goals: 营养目标（高蛋白/控油/控糖/增肌/减脂）；为空时使用已保存画像。
        dietary_restrictions: 忌口/过敏，逗号分隔（如 "不吃辣,猪肉"）；为空时使用已保存画像。
        top_k: 返回数量，默认 5。
    """
    from db import get_db

    db = get_db()
    # 合并已存画像：显式入参优先，缺省值回落到 user_profile
    saved = db.get_user_profile() or {}
    try:
        budget_f = float(budget)
    except (TypeError, ValueError):
        budget_f = 0
    if not budget_f or budget_f < 0:
        budget_f = float(saved.get("budget") or 20)
    effective_budget = budget_f
    effective_prefs = preferences if preferences else saved.get("flavor_preferences", "")
    effective_goal = health_goals if health_goals else saved.get("health_goals", "")
    effective_restr = dietary_restrictions if dietary_restrictions else saved.get("dietary_restrictions", "")

    if not top_k or top_k < 0:
        top_k = 5

    user_profile = {
        "budget": effective_budget,
        "flavor_preferences": effective_prefs,
        "health_goals": effective_goal,
        "dietary_restrictions": effective_restr,
    }
    dishes = db.get_all_dishes()
    # 预算硬约束：价格 > 预算的菜品直接排除
    dishes = [d for d in dishes if float(d["price"]) <= effective_budget]
    # 忌口硬约束：剔除命中忌口/过敏的菜品
    dishes = filter_by_restrictions(dishes, effective_restr)
    scored = score_dishes(dishes, user_profile, budget=effective_budget)
    return scored[:top_k]