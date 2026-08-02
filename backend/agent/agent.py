from langchain.agents import create_agent
from llm.client import get_llm
from tools.search import search_dish, get_all_dishes

tools = [search_dish, get_all_dishes]

SYSTEM_PROMPT = (
    "You are a helpful canteen meal assistant. You help users find dishes "
    "and nutrition info. Use the search_dish tool to find dishes by name or keyword. "
    "Use get_all_dishes to list all available dishes. "
    "Always respond in Chinese."
)


def create_agent_executor():
    llm = get_llm()
    agent = create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent