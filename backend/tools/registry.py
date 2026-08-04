"""工具注册中心（B 拥有）

集中收集全部 @tool，供 agent 注册。新增工具在此登记即可。
"""
from tools.search import search_dish, get_all_dishes
from tools.scoring import recommend
from tools.optimizer import optimize_meal_tool
from tools.meal_recommend import recommend_for_meal
from tools.record import (
    record_meal,
    confirm_record,
    reject_record,
    get_pending_records,
    get_pending_records_by_date,
    get_pending_record,
    confirm_records,
    reject_records,
    get_daily_intake,
    get_day_total,
    get_weekly_trend,
    get_weekly_summary,
)
from rag.retriever import retrieve_dishes
from agent.subagent import optimize_meal_subagent
from store.profile import set_user_profile, get_user_profile_tool
from mcp.weather_tool import get_weather_recommendation

ALL_TOOLS = [
    search_dish,
    get_all_dishes,
    retrieve_dishes,
    recommend,
    recommend_for_meal,
    optimize_meal_tool,
    optimize_meal_subagent,
    get_weather_recommendation,
    record_meal,
    confirm_record,
    reject_record,
    get_pending_records,
    get_pending_records_by_date,
    get_pending_record,
    confirm_records,
    reject_records,
    get_daily_intake,
    get_day_total,
    get_weekly_trend,
    get_weekly_summary,
    set_user_profile,
    get_user_profile_tool,
]