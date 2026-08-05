# 部署说明（DEPLOY）

> 版本：v1.1　|　日期：2026-08-03
> 维护：C（B 协助 ollama 服务部分）

---

## 1. 部署架构

```
frontend (nginx :8080) ──▶ backend (FastAPI :8000) ──▶ ollama (本地 LLM)
       │  /api 反代             │
       │                        └──▶ mcp-weather (天气 MCP 独立进程)
```

- `frontend`：nginx 托管 Vue 构建产物，SPA 路由回退，`/api/*` 反向代理到 backend
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
# 前端:  http://localhost:8080
# 后端:  http://localhost:8000/docs
# Ollama: http://localhost:11434
```

> 前端容器构建时注入 `VITE_API_BASE=/api`，浏览器请求走同域 `/api`，
> 由 nginx `proxy_pass http://backend:8000/` 去前缀转发到后端。
> 端口映射：`8080:80`（nginx），如需换端口改 `docker-compose.yml`。

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

# 前端（Node 18+）
cd frontend
npm install
npm run dev        # http://localhost:5173（dev 直连 http://localhost:8000）
npm run build      # 产物在 dist/，可静态托管或 nginx 托管
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
- 一律走 `../backend/.env`，`WEATHER_API_KEY` / `OPENAI_API_KEY` 不入镜像
- compose 中天气 key 通过环境变量透传，不写死

### 4.6 前端刷新 /trend 等路由返回 404
- 已配置 SPA 回退：nginx `try_files $uri $uri/ /index.html`（见 `docker/nginx.conf`）
- 若自建 nginx 忘了此项，SPA 深链接刷新会 404

### 4.7 流式回复在代理后不逐字显示
- nginx 需对 `/api` 关闭缓冲：`proxy_buffering off; proxy_cache off;`（已配置）
- 否则 `/chat/stream` 的 SSE 增量被 nginx 攒起来一次返回

### 4.8 前端连不上后端
- 生产（Docker）：前端通过 `/api` 反代，无需知道后端地址，检查 nginx 日志
- 本地 dev：`VITE_API_BASE` 默认 `http://localhost:8000`，见 `frontend/.env.development`

## 5. 远程 LLM / Embedding 服务器（可选）

可将 LLM 与 embedding 独立部署到一台服务器，后端通过网络访问，不占用本机资源。

**已部署：`119.45.135.201:11434`（Ubuntu · 4 核 · 15G · 无 GPU，CPU 推理）**

```bash
# 服务器上：安装 ollama（大陆服务器网络受限时用 github 代理，如 gh-proxy.com）
curl -fsSL https://ollama.com/install.sh | sh   # 或从 gh-proxy 下载 tar.zst 手动安装

# 配置 systemd 监听 0.0.0.0（OLLAMA_HOST=0.0.0.0:11434）后：
ollama pull qwen2.5:7b    # LLM（CPU 推理，支持 function calling/tools）
ollama pull bge-m3        # Embedding（1024 维）
```

- 腾讯云安全组需放行入站 `TCP 11434`
- 验证：`curl http://<ip>:11434/api/version` → `{"version":"0.32.5"}`
- 后端指向（`backend/.env`）：

```
OLLAMA_BASE_URL=http://119.45.135.201:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_EMBED_MODEL=bge-m3
```

> 注意：`qwen3.5:7b` 在 ollama 库不存在；`qwen2.5:7b` 为替代（同样支持工具调用）。
> CPU 推理较慢，对话/工具调用每轮约 5~30s，演示时耐心等待或改小模型（`qwen2.5:3b`）。
> 远程 CPU 场景建议调大 `LLM_TIMEOUT`（`backend/.env` 设为 `120`~`180`），避免 Agent 工具循环因慢推理被超时中断。

### 5.1 Ollama 服务性能优化（4H16G 无 GPU 实测）

在 systemd 服务中追加以下环境变量，显著降低对话延迟：

```bash
sudo tee /etc/systemd/system/ollama.service > /dev/null <<'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ubuntu
Group=ubuntu
Environment=OLLAMA_HOST=0.0.0.0:11434
Environment=OLLAMA_KEEP_ALIVE=24h
Environment=OLLAMA_NUM_PARALLEL=2
Environment=OLLAMA_MAX_LOADED_MODELS=2
Environment=OLLAMA_KV_CACHE_TYPE=q8_0
Environment=OLLAMA_CONTEXT_LENGTH=4096
Environment=OLLAMA_FLASH_ATTENTION=1
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload && sudo systemctl restart ollama
```

**各参数作用与实测效果**（4 核 AMD EPYC / 15G，qwen2.5:7b Q4_K_M + bge-m3 常驻）：

| 参数 | 值 | 作用 |
|------|-----|------|
| `OLLAMA_KEEP_ALIVE` | `24h` | 模型常驻内存，**避免冷加载**（冷加载一次可达 83s+） |
| `OLLAMA_NUM_PARALLEL` | `2` | 双并发 slot，请求不互相排队 |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` | KV 缓存 8bit 量化，省内存 |
| `OLLAMA_CONTEXT_LENGTH` | `4096` | 明确上下文长度（配合并行度实际 8192） |
| `OLLAMA_FLASH_ATTENTION` | `1` | 开启 FA 加速 |
| `OLLAMA_MAX_LOADED_MODELS` | `2` | 7b 与 bge-m3 同时常驻 |

**实测性能对比**（远程 /api/chat）：

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 单次 LLM 调用（热模型） | 180s 超时 | **~1.0s** |
| Agent 简单对话 | 超时 | **~2.5s** |
| Agent 工具调用对话 | 120s 超时 | **~10~18s** |
| 并发 embedding + chat | 24s | **~3.8s** |

**关键经验**：
1. **冷加载是最大坑**：首次请求或模型被卸载后再请求，`load_duration` 可达 80s+，会表现为"无回复"。`KEEP_ALIVE=24h` + 内存充足（7b 5.2G + bge-m3 1.2G + 系统 < 8G，15G 够用）可完全避免。
2. **热模型下性能正常**：7B 模型 prompt 处理约 0.15s/500token，eval 约 7~9 tok/s。线程数（`num_threads` 2 vs 4）影响可忽略，不必调。
3. **embedding 与 chat 并发**：同时触发 RAG embedding 与 7b 推理会抢占 CPU（冷态下明显），热模型下影响有限（3.8s）。如需更稳可把 `OLLAMA_NUM_PARALLEL` 降为 1 强制串行。
4. **防止模型跑飞**：后端 `llm/client.py` 的 `ChatOllama` 已加 `model_kwargs={"num_predict": 512}`，限制单次生成上限，避免无限输出占满并发 slot。
5. **换小模型受限**：服务器拉取 `qwen2.5:3b`（1.9G）从 ollama.com 仅 ~500KB/s，需 50 分钟+，大陆网络不现实；7B 已是该配置合理上限。

## 6. 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `USE_CLOUD_API` | `false` | **LLM 开关**：`true`=云端 API，`false`=本地 Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | 本地；Docker 内 `http://ollama:11434` |
| `OLLAMA_MODEL` | `qwen2.5:7b` | 本地模型 |
| `OPENAI_API_KEY` | 空 | 云端 LLM（`USE_CLOUD_API=true` 时必填） |
| `LLM_TIMEOUT` | `60` | LLM 请求超时秒 |
| `LLM_MAX_RETRIES` | `2` | LLM 重试次数 |
| `WEATHER_API_KEY` | 空 | 高德天气 key（可选，mock 回退） |
| `WEATHER_BASE_URL` | `https://restapi.amap.com/v3/weather/weatherInfo` | 天气接口 |
| `GEOCODE_BASE_URL` | `https://restapi.amap.com/v3/geocode/geo` | 地理编码接口 |
| `DB_PATH` | `backend/data/canteen.db` | SQLite 路径 |
| `CHROMA_DB_PATH` | `backend/data/chroma_db` | Chroma 向量库路径 |
| `VITE_API_BASE`（构建时） | `/api` | 前端后端地址；本地 dev 用 `http://localhost:8000` |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | RAG embedding 模型；远程用 `bge-m3` |