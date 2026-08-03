from langchain.agents import create_agent
from llm.client import get_llm
from tools.search import search_dish, get_all_dishes
from tools.scoring import recommend
from tools.optimizer import optimize_meal_tool
from tools.record import (
    record_meal,
    confirm_record,
    reject_record,
    get_pending_records,
    get_daily_intake,
    get_day_total,
    get_weekly_trend,
    get_weekly_summary,
)
from rag.retriever import retrieve_dishes
from agent.subagent import optimize_meal_subagent

tools = [
    search_dish,
    get_all_dishes,
    retrieve_dishes,
    recommend,
    optimize_meal_tool,
    optimize_meal_subagent,
    record_meal,
    confirm_record,
    reject_record,
    get_pending_records,
    get_daily_intake,
    get_day_total,
    get_weekly_trend,
    get_weekly_summary,
]

SYSTEM_PROMPT = (
    "You are a helpful canteen meal assistant. You help users find dishes "
    "and nutrition info. Use the search_dish tool to find dishes by name or keyword. "
    "Use get_all_dishes to list all available dishes. "
    "Use retrieve_dishes to search dishes by semantic/keyword description (fuzzy match). "
    "Use recommend to recommend dishes based on budget, flavor preference, and health goals. "
    "Use optimize_meal_tool to find the best meal combination under a budget and calorie limit. "
    "Use optimize_meal_subagent to delegate the whole meal-planning task to a specialist agent. "
    "Use record_meal to record a meal intake, then confirm_record to confirm it. "
    "Use get_daily_intake / get_day_total to view nutrition by day. "
    "Use get_weekly_trend / get_weekly_summary to view weekly nutrition trends. "
    "Always respond in Chinese. When recommending, explain why each dish is recommended. "
    "When the user confirms recording a meal, first call record_meal then confirm_record."
)


def create_agent_executor():
    llm = get_llm()
    agent = create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent