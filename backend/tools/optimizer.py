"""
组合优化算法：最优一餐搭配（A 拥有 · 自研核心）

问题：给定预算（元）+ 热量上限（kcal），从菜品库中选若干道菜组成一餐，
约束：
    1. 总价格 ≤ 预算
    2. 总热量 ≤ 热量上限
    3. 荤素搭配合理：至少 1 荤 + 1 素 + 1 主食
目标：在满足约束的前提下，最大化蛋白质总量（高蛋白膳食导向）。

算法：二维 01 背包（动态规划）
    dp[price][calories] = 最大蛋白质(g)
    每道菜为 01 背包物品（选 1 次），价格/热量为双维容量。
    背包得到初始解后，若荤素搭配不满足，用"贪心替换"修正：
      优先用更合适的同类别菜替换，保证 1 荤 + 1 素 + 1 主食 齐全。

系数与说明详见 docs/评分公式说明.md 的"组合优化"章节。
"""
from typing import Optional

from langchain_core.tools import tool

# 荤素搭配要求
REQUIRED_CATEGORIES = ("荤菜", "素菜", "主食")


def _as_float(d: dict, key: str) -> float:
    return float(d.get(key, 0))


def optimize_meal(dishes: list[dict], budget: float, calorie_limit: float,
                  user_profile: Optional[dict] = None) -> dict:
    """给定预算与热量上限，用背包 DP 求最优一餐搭配。

    Args:
        dishes: 菜品列表（含 id/name/price/calories/protein/...）
        budget: 预算（元）
        calorie_limit: 热量上限（kcal）
        user_profile: 用户画像（可选，用于口味偏好调整评分）
    Returns:
        dict: 含 dishes（选中菜品）、total_price、total_calories、
              total_protein、categories、balance_ok、reason
    """
    if budget <= 0 or calorie_limit <= 0:
        return _empty_result("预算或热量上限必须大于 0")

    candidates = [
        d for d in dishes
        if _as_float(d, "price") <= budget + 1e-6
        and _as_float(d, "calories") <= calorie_limit + 1e-6
    ]
    if not candidates:
        return _empty_result("预算/热量约束下无任何可行菜品")

    # 二维 01 背包
    max_price = int(budget)
    max_cal = int(calorie_limit)
    NEG = -1e9
    # dp[p][c] = 最大蛋白质
    dp = [[NEG] * (max_cal + 1) for _ in range(max_price + 1)]
    # choice[p][c] = 达到该状态选择的菜品索引（-1 表示未选）
    choice = [[-1] * (max_cal + 1) for _ in range(max_price + 1)]
    dp[0][0] = 0.0

    for idx, d in enumerate(candidates):
        price = int(round(_as_float(d, "price")))
        cal = int(round(_as_float(d, "calories")))
        prot = _as_float(d, "protein")
        for p in range(max_price, price - 1, -1):
            for c in range(max_cal, cal - 1, -1):
                prev = dp[p - price][c - cal]
                if prev > NEG and prev + prot > dp[p][c]:
                    dp[p][c] = prev + prot
                    choice[p][c] = idx

    # 找出全局最优（不必恰好装满）
    best_p, best_c, best_prot = 0, 0, 0.0
    for p in range(max_price + 1):
        for c in range(max_cal + 1):
            if dp[p][c] > best_prot:
                best_prot = dp[p][c]
                best_p, best_c = p, c

    if best_prot <= 0:
        return _empty_result("无法在约束内组成搭配")

    # 回溯得到选中菜品索引
    selected_idx = []
    p, c = best_p, best_c
    while p > 0 or c > 0:
        idx = choice[p][c]
        if idx < 0:
            break
        selected_idx.append(idx)
        p -= int(round(_as_float(candidates[idx], "price")))
        c -= int(round(_as_float(candidates[idx], "calories")))

    selected = [candidates[i] for i in reversed(selected_idx)]

    # 荤素搭配修正
    selected, balance_ok, reason = _ensure_balance(selected, candidates,
                                                   budget, calorie_limit,
                                                   user_profile)

    return _build_result(selected, budget, calorie_limit, balance_ok, reason)


def _ensure_balance(selected: list[dict], candidates: list[dict],
                    budget: float, calorie_limit: float,
                    user_profile: Optional[dict] = None) -> tuple:
    """确保 1 荤 + 1 素 + 1 主食；缺类别时尝试补足/替换。
    策略：先尝试直接补足；若空间不够，尝试移除 1~2 道后再补足，
    取补足后（融合偏好的评分）最高的可行方案。"""
    from itertools import combinations

    required = set(REQUIRED_CATEGORIES)

    def missing_cats(sels: list[dict]) -> list[str]:
        cats = {d.get("category") for d in sels}
        return [c for c in REQUIRED_CATEGORIES if c not in cats]

    def total_metrics(sels: list[dict]) -> tuple:
        return (sum(_as_float(d, "price") for d in sels),
                sum(_as_float(d, "calories") for d in sels),
                sum(_as_float(d, "protein") for d in sels))

    def dish_value(d: dict) -> float:
        """补足时选择该菜的价值：有画像用评分（含偏好），否则蛋白质。"""
        if user_profile:
            try:
                # 兼容两种运行环境：backend 在 sys.path（tools.scoring）或 tools 目录在 path（scoring）
                from tools.scoring import score_dish
            except ImportError:
                try:
                    from scoring import score_dish
                except ImportError:
                    score_dish = None
            if score_dish is not None:
                try:
                    return score_dish(d, user_profile, budget=budget)["score"]
                except Exception:
                    pass
        return _as_float(d, "protein")

    def try_fill(cur: list[dict]) -> tuple:
        """尝试补足缺失类别（贪心选评分/蛋白质最高的可行菜），返回 (结果, 是否补齐)。"""
        cur = list(cur)
        while missing_cats(cur):
            m = missing_cats(cur)[0]
            cur_price, cur_cal, _ = total_metrics(cur)
            best_d = None
            best_val = -1.0
            for d in candidates:
                if d.get("category") != m:
                    continue
                if (_as_float(d, "price") <= budget - cur_price + 1e-6
                        and _as_float(d, "calories") <= calorie_limit - cur_cal + 1e-6):
                    val = dish_value(d)
                    if val > best_val:
                        best_val = val
                        best_d = d
            if best_d is None:
                break
            cur.append(best_d)
        return cur, (not missing_cats(cur))

    # 尝试删除 0/1/2 道后补足，比较时用评分（含偏好）或蛋白质
    best_solution, best_val = None, -1.0
    for remove_count in range(0, 3):
        for removed in combinations(range(len(selected)), remove_count):
            base = [selected[i] for i in range(len(selected)) if i not in removed]
            filled, ok = try_fill(base)
            if ok:
                val = sum(dish_value(d) for d in filled)
                if val > best_val:
                    best_val = val
                    best_solution = filled
    if best_solution:
        return best_solution, True, "荤素搭配合理（已补足）"

    missing = missing_cats(selected)
    return selected, False, f"缺少类别: {', '.join(missing)}，无法补足"


def _build_result(selected, budget, calorie_limit, balance_ok, reason) -> dict:
    total_price = sum(_as_float(d, "price") for d in selected)
    total_cal = sum(_as_float(d, "calories") for d in selected)
    total_prot = sum(_as_float(d, "protein") for d in selected)
    total_carbs = sum(_as_float(d, "carbs") for d in selected)
    total_fat = sum(_as_float(d, "fat") for d in selected)
    cats = {}
    for d in selected:
        cats[d.get("category")] = cats.get(d.get("category"), 0) + 1

    return {
        "dishes": selected,
        "total_price": round(total_price, 2),
        "total_calories": round(total_cal, 1),
        "total_protein": round(total_prot, 1),
        "total_carbs": round(total_carbs, 1),
        "total_fat": round(total_fat, 1),
        "categories": cats,
        "budget": float(budget),
        "calorie_limit": float(calorie_limit),
        "balance_ok": balance_ok,
        "reason": reason,
    }


def _empty_result(reason: str) -> dict:
    return {
        "dishes": [], "total_price": 0.0, "total_calories": 0.0,
        "total_protein": 0.0, "total_carbs": 0.0, "total_fat": 0.0,
        "categories": {}, "budget": 0.0, "calorie_limit": 0.0,
        "balance_ok": False, "reason": reason,
    }


# =============================================================================
# @tool：组合优化接口（B 的 agent 可注册调用）
# =============================================================================

@tool
def optimize_meal_tool(budget: float, calorie_limit: float,
                       preferences: str = "") -> dict:
    """在预算与热量上限内，用组合算法求最优一餐搭配（荤素搭配合理）。
    Args:
        budget: 预算（元/餐）
        calorie_limit: 热量上限（kcal）
        preferences: 口味偏好（逗号分隔），可选；不传时使用已保存的用户画像。
    """
    from db import get_db

    db = get_db()
    saved = db.get_user_profile() or {}
    effective_prefs = preferences if preferences else saved.get("flavor_preferences", "")
    user_profile = {
        "budget": float(budget),
        "flavor_preferences": effective_prefs,
        "health_goals": saved.get("health_goals", ""),
    }
    dishes = db.get_all_dishes()
    return optimize_meal(dishes, budget, calorie_limit, user_profile=user_profile)