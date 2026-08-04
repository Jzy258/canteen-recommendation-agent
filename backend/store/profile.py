"""用户画像长期记忆（B 拥有 · Store · D5）

基于 A 的 user_profile 表：读取 → 对话注入 → 更新。
- get_profile(): 读取最近一条画像
- save_profile(...): upsert 预算/口味/忌口/健康目标
- build_context(): 生成注入对话的摘要文本（供 Agent 上下文）
- summarize_nutrition(): 汇总近 N 天营养到 nutrition_summary（长期记忆）
"""
import json

from langchain_core.tools import tool
from middleware.logger_config import get_logger

logger = get_logger("canteen.store")


def _db():
    from db import get_db
    return get_db()


def get_profile() -> dict | None:
    return _db().get_user_profile()


def save_profile(budget: float = 0, flavor_preferences: str = "",
                 dietary_restrictions: str = "", health_goals: str = "") -> int:
    """持久化用户画像，返回 profile id。"""
    pid = _db().upsert_user_profile(
        budget=budget,
        flavor_preferences=flavor_preferences,
        dietary_restrictions=dietary_restrictions,
        health_goals=health_goals,
    )
    logger.info("用户画像保存 | id=%s budget=%s pref=%s goal=%s",
                pid, budget, flavor_preferences, health_goals)
    return pid


def summarize_nutrition(days: int = 7) -> dict | None:
    """汇总近 N 天营养到 user_profile.nutrition_summary。返回新汇总 dict。"""
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=days - 1)
    trend = _db().get_weekly_trend(end_date=end.isoformat(), days=days)
    confirmed = [t for t in trend if t.get("total_calories", 0) > 0]
    summary = {
        "days": len(confirmed),
        "total_calories": round(sum(t.get("total_calories", 0) for t in confirmed), 1),
        "total_protein": round(sum(t.get("total_protein", 0) for t in confirmed), 1),
        "avg_calories": round(sum(t.get("total_calories", 0) for t in confirmed)
                              / max(len(confirmed), 1), 1),
        "avg_protein": round(sum(t.get("total_protein", 0) for t in confirmed)
                             / max(len(confirmed), 1), 1),
        "week_key": end.isoformat(),
    }
    _db().update_nutrition_summary(json.dumps(summary, ensure_ascii=False))
    return summary


def build_context() -> str:
    """生成注入 Agent 上下文的用户画像摘要文本。"""
    p = get_profile()
    if not p:
        return "用户画像为空（尚未设置预算/偏好）。"
    parts = []
    if p.get("budget"):
        parts.append(f"预算 {p['budget']} 元/餐")
    if p.get("flavor_preferences"):
        parts.append(f"口味偏好: {p['flavor_preferences']}")
    if p.get("dietary_restrictions"):
        parts.append(f"忌口: {p['dietary_restrictions']}")
    if p.get("health_goals"):
        parts.append(f"健康目标: {p['health_goals']}")
    summary = p.get("nutrition_summary") or ""
    if summary:
        try:
            s = json.loads(summary)
            parts.append(f"近{s.get('days', '?')}天日均热量 {s.get('avg_calories', 0)}kcal")
        except Exception:
            pass
    return "；".join(parts) if parts else "用户画像为空。"


# =============================================================================
# @tool：画像读写
# =============================================================================

@tool
def set_user_profile(budget: float = 0, flavor_preferences: str = "",
                     dietary_restrictions: str = "", health_goals: str = "") -> str:
    """保存/更新用户画像（预算、口味偏好、忌口、健康目标）。返回确认信息。"""
    pid = save_profile(budget, flavor_preferences, dietary_restrictions, health_goals)
    return f"用户画像已保存 (id={pid})"


@tool
def get_user_profile_tool() -> str:
    """读取当前用户画像摘要。"""
    return build_context()