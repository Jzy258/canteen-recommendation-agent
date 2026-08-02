from langchain.agents import create_agent
from llm.client import get_llm
from tools.search import search_dish, get_all_dishes
from tools.recommend import recommend_dishes

tools = [search_dish, get_all_dishes, recommend_dishes]

SYSTEM_PROMPT = (
    "You are a helpful canteen meal assistant. You help users find dishes "
    "and nutrition info. Use the search_dish tool to find dishes by name or keyword. "
    "Use get_all_dishes to list all available dishes. "
    "Use recommend_dishes to recommend dishes based on budget, category preference, "
    "flavor preference, and health goal. "
    "Always respond in Chinese. When recommending, explain why each dish is recommended."
)


def create_agent_executor():
    llm = get_llm()
    agent = create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent