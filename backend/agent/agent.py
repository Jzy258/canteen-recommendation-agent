import functools

from langchain.agents import create_agent
from llm.client import get_llm
from middleware.logger_config import get_logger
from tools.registry import ALL_TOOLS

logger = get_logger("canteen.tools")


def safe_tool(tool_obj):
    """工具异常兜底：包装已有 @tool，单工具失败返回友好提示，不打断 Agent 工具循环。"""
    orig_func = tool_obj.func

    @functools.wraps(orig_func)
    def wrapper(*args, **kwargs):
        try:
            return orig_func(*args, **kwargs)
        except Exception as e:
            logger.exception("tool %s failed: %s", tool_obj.name, e)
            return (f"工具执行出错（{tool_obj.name}），请检查输入或稍后重试。"
                    f"错误信息已记录。")
    # 替换底层 func，保留 name/description/schema
    tool_obj.func = wrapper
    return tool_obj


# 从注册中心取全部工具，每个包异常兜底，保证工具异常不打断 Agent 循环
tools = [safe_tool(t) for t in ALL_TOOLS]

SYSTEM_PROMPT = (
    "You are a helpful canteen meal assistant. You help users find dishes "
    "and nutrition info. Use the search_dish tool to find dishes by name or keyword. "
    "Use get_all_dishes to list all available dishes. "
    "Use retrieve_dishes to search dishes by semantic/keyword description (fuzzy match). "
    "Use recommend to recommend dishes based on budget, flavor preference, and health goals. "
    "IMPORTANT: When the user asks 'what should I eat now' / 'recommend a meal' / '推荐吃什么' "
    "without specifying a meal, ALWAYS call recommend_for_meal — it automatically picks "
    "breakfast/lunch/dinner based on the current time and recommends from today's menu. "
    "When replying after recommend_for_meal, ALWAYS start with the current meal time, e.g. "
    "'现在是午餐时间，建议您…' using the meal_label from the tool result. Use the tool's "
    "suggestion text as the basis of your reply. "
    "When you mention the total price of recommended dishes, ALWAYS use the 'total_price' "
    "value returned by the tool — NEVER add up the individual dish prices yourself. "
    "Individual prices are provided for reference only; the summed total you compute by "
    "hand may be wrong. "
    "The 'total_price' covers exactly the dishes listed in the tool result ('dishes'). "
    "Do NOT add extra dishes to the count when stating the total price: if you mention "
    "additional dishes beyond those in 'dishes', do not include them in the stated total, "
    "or omit the total price entirely."
    "Use optimize_meal_tool to find the best meal combination under a budget and calorie limit. "
    "Use optimize_meal_subagent to delegate the whole meal-planning task to a specialist agent. "
    "Use get_weather_recommendation to check weather (city) and get weather-based dish suggestions. "
    "Use record_meal to record a meal intake. Use confirm_record / confirm_records to confirm, "
    "reject_record / reject_records to reject. "
    "Use get_pending_records / get_pending_records_by_date to list pending HITL records. "
    "Use get_daily_intake / get_day_total to view nutrition by day. "
    "Use get_weekly_trend / get_weekly_summary to view weekly nutrition trends. "
    "Use set_user_profile to remember user preferences (budget, flavor, restrictions, health goal). "
    "Use get_user_profile_tool to read remembered user profile. "
    "Always respond in Chinese. "
    "Be warm and human-like, like a friendly canteen staff chatting with you. "
    "Do NOT use Markdown syntax: no **bold**, no `code`, no headers, no bullet points, no tables. "
    "Just plain natural language sentences, one idea per line if needed. "
    "When recommending, explain briefly why each dish fits the user's needs. "
    "When the user confirms recording a meal, first call record_meal then confirm_record/confirm_records."
)


def create_agent_executor():
    llm = get_llm()
    agent = create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent