# llm — LLM 供应商适配

**所有者：B · Agent 与 LLM**

- 默认：`ollama.py`（`langchain-ollama` 连接本地模型，如 qwen2.5）
- 预留：`cloud.py`（OpenAI 兼容云端 API，可切换）
- 统一工厂函数：`get_llm()`，配置走 `../.env`