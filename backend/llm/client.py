import os
from dotenv import load_dotenv

load_dotenv()


def _use_cloud() -> bool:
    """读取 USE_CLOUD_API 开关（true/false，大小写不敏感）。"""
    return os.getenv("USE_CLOUD_API", "").strip().lower() in ("1", "true", "yes", "on")


def get_llm():
    timeout = int(os.getenv("LLM_TIMEOUT", "60"))
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # 显式开关：USE_CLOUD_API=true 走云端，否则走本地 Ollama
    if _use_cloud():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "USE_CLOUD_API=true 但未配置 OPENAI_API_KEY，请检查 .env。"
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL"),
            temperature=0.3,
            timeout=timeout,
            max_retries=max_retries,
        )

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=0.3,
            timeout=timeout,
            max_retries=max_retries,
        )
    except Exception:
        pass

    raise RuntimeError(
        "No LLM configured. Set USE_CLOUD_API=true + OPENAI_API_KEY for cloud API, "
        "or OLLAMA_BASE_URL for local Ollama."
    )