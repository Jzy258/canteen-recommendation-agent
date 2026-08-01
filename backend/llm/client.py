import os
from dotenv import load_dotenv

load_dotenv()


def get_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL"),
            temperature=0.3,
        )

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(base_url=base_url, model=model, temperature=0.3)
    except Exception:
        pass

    raise RuntimeError(
        "No LLM configured. Set OPENAI_API_KEY for cloud API, "
        "or OLLAMA_BASE_URL for local Ollama."
    )