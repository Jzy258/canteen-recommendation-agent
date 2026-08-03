# 部署说明（DEPLOY）

> 版本：v1.0　|　日期：2026-08-03
> 维护：C（B 协助 ollama 服务部分）

---

## 1. 部署架构

```
frontend (nginx) ──▶ backend (FastAPI) ──▶ ollama (本地 LLM)
                       │
                       └──▶ mcp-weather (天气 MCP 独立进程)
```

- `backend`：FastAPI，承载 Agent / 工具 / RAG / 中间件 / Store
- `ollama`：本地 LLM 服务（模型挂载卷，避免重复下载）
- `mcp-weather`：天气 MCP 独立进程（mock 或高德真实 API）

## 2. 一键启动（Docker Compose）

```bash
# 准备配置
cp .env.example .env
# （可选）填写天气 API key
# WEATHER_API_KEY=...

# 构建并启动
docker compose -f docker/docker-compose.yml up -d --build

# 查看日志
docker compose -f docker/docker-compose.yml logs -f backend

# 访问
# 后端: http://localhost:8000/docs
# Ollama: http://localhost:11434
```

## 3. 本地开发（无 Docker）

```bash
# 后端
cd backend
uv sync
uv run python main.py

# 初始化数据库（建表 + 导入菜品/菜单数据，首次必须执行）
# 已在 backend 目录下，故用 data/init_db.py
uv run python data/init_db.py

# Ollama（需本机安装 ollama）
ollama serve
ollama pull qwen2.5:7b

# 天气 MCP（可选独立进程）
uv run python backend/mcp/weather_server.py
```

> 数据库初始化说明（A 拥有）：`init_db.py` 执行 `db/schema.sql` 建表，
> 并从 `dishes.csv`（54 道菜）、`menu.csv`（5天×3餐）灌入数据，幂等可重复执行。

## 4. 常见坑

### 4.1 Ollama 模型下载慢 / 显存不足
- 模型挂载到 Docker 卷 `ollama-models`，首次下载后不重复拉取
- 显存不足选 7B 量化模型（`qwen2.5:7b`）；可用 `ollama pull qwen2.5:3b` 更轻

### 4.2 后端连不上 ollama
- Docker 内 `OLLAMA_BASE_URL` 必须指向 `http://ollama:11434`（服务名，非 localhost）
- 本地开发用 `http://localhost:11434`
- 排查：`docker exec canteen-backend curl http://ollama:11434`

### 4.3 本地 mcp 包遮蔽 SDK
- `backend/mcp/` 与 MCP SDK 同名，若报 `ModuleNotFoundError: mcp.server`
  → 用脚本路径运行：`python backend/mcp/weather_server.py`，不要用 `-m backend.mcp`

### 4.4 Chroma 持久化
- 向量库写入 `backend/data/chroma_db`，通过数据卷 `canteen-data` 持久化
- 数据变更后 RAG 索引按菜品签名自动重建

### 4.5 密钥
- 一律走 `.env`，`WEATHER_API_KEY` / `OPENAI_API_KEY` 不入镜像
- compose 中天气 key 通过环境变量透传，不写死

## 5. 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | 本地；Docker 内 `http://ollama:11434` |
| `OLLAMA_MODEL` | `qwen2.5:7b` | 本地模型 |
| `OPENAI_API_KEY` | 空 | 云端 LLM 切换（可选） |
| `LLM_TIMEOUT` | `60` | LLM 请求超时秒 |
| `LLM_MAX_RETRIES` | `2` | LLM 重试次数 |
| `WEATHER_API_KEY` | 空 | 高德天气 key（可选，mock 回退） |
| `WEATHER_BASE_URL` | `https://restapi.amap.com/v3/weather/weatherInfo` | 天气接口 |
| `GEOCODE_BASE_URL` | `https://restapi.amap.com/v3/geocode/geo` | 地理编码接口 |
| `DB_PATH` | `backend/data/canteen.db` | SQLite 路径 |
| `CHROMA_DB_PATH` | `backend/data/chroma_db` | Chroma 向量库路径 |
