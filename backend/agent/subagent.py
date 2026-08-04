"""
搭配优化子 Agent（B 拥有）

职责：专注"给定预算 + 热量上限求最优一餐搭配"单一任务。
主 Agent 将该子 Agent 包装为工具调用（agent 即工具），
子 Agent 内部持有 optimize_meal_tool，输出最优搭配 + 营养汇总 + 建议。
"""
import logging

from langchain.agents import create_agent
from langchain_core.tools import tool
from llm.client import get_llm
from tools.optimizer import optimize_meal_tool

_SUB_TOOLS = [optimize_meal_tool]

_SUB_PROMPT = (
    "You are a meal-optimization specialist. Your ONLY job: given a budget (元) "
    "and calorie limit (kcal), use the optimize_meal_tool to find the best meal "
    "combination (balanced 荤素). "
    "Use optimize_meal_tool with budget and calorie_limit. "
    "If balance_ok is False, explain the constraint issue and suggest relaxing. "
    "Always respond in Chinese, warm and human-like, in plain natural language. "
    "Do NOT use Markdown syntax: no **bold**, no `code`, no headers, no bullets, no tables. "
    "Include the meal combination, total price, total calories, total protein, and a nutrition tip."
)


def create_optimizer_subagent():
    llm = get_llm()
    return create_agent(
        llm,
        _SUB_TOOLS,
        system_prompt=_SUB_PROMPT,
    )


@tool
def optimize_meal_subagent(budget: float, calorie_limit: float,
                           preferences: str = "") -> str:
    """委托给搭配优化子 Agent：在预算与热量上限内求最优一餐，返回中文搭配方案。
    Args:
        budget: 预算（元/餐）
        calorie_limit: 热量上限（kcal）
        preferences: 口味偏好（逗号分隔），可选
    """
    from tools.optimizer import optimize_meal_tool
    try:
        agent = get_subagent()
        result = agent.invoke({
            "messages": [
                _human(f"预算 {budget} 元，热量上限 {calorie_limit} kcal"
                       f"{('，口味偏好 ' + preferences) if preferences else ''}，"
                       "请搭配最优一餐。")
            ]
        })
        return result["messages"][-1].content
    except Exception as e:
        # 子 Agent 依赖 LLM，失败时降级为直接调用组合优化工具
        logging.warning("subagent failed (%s), fallback to optimize_meal_tool", e)
        r = optimize_meal_tool.invoke({"budget": budget, "calorie_limit": calorie_limit})
        if not r["dishes"]:
            return f"无法在约束内组成搭配：{r.get('reason', '')}"
        names = "、".join(d["name"] for d in r["dishes"])
        return (f"预算 {r['total_price']} 元 / 热量 {r['total_calories']} kcal / "
                f"蛋白质 {r['total_protein']}g。搭配：{names}。"
                f"（子 Agent 暂不可用，已降级为直接组合优化）")


def _human(text: str):
    from langchain_core.messages import HumanMessage
    return HumanMessage(content=text)


# 子 Agent 单例（复用 LLM 连接）
_subagent = None


def get_subagent():
    global _subagent
    if _subagent is None:
        _subagent = create_optimizer_subagent()
    return _subagent