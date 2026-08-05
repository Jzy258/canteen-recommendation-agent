---
name: canteen-dev
description: 食堂推荐 Agent（FastAPI + LangChain + Vue3）项目的开发、测试、部署与数据维护技能。在修改后端工具/Agent 链路、前端页面、数据库、运行测试或部署到 ginna.cn 时使用。
---

# 食堂推荐 Agent · 项目技能（SKILL）

## 1. 项目速览

- 后端：FastAPI + LangChain Agent + SQLite（`backend/`）
- 前端：Vue3 + TS + Element Plus + ECharts（`frontend/`，Vite）
- LLM：云端 API（`USE_CLOUD_API=true`）或本地/远程 Ollama（qwen2.5:7b）
- RAG：Chroma（`backend/rag/retriever.py`，embedding bge-m3）
- 版本：SemVer 单一来源 `backend/version.py` + `pyproject.toml`（当前 v1.3.0）

## 2. 常用命令

### 初始化数据库（新建/重建）
```bash
cd backend
uv run python data/init_db.py    # 建表 + 导入 100 道菜/菜单
```
> ⚠️ 别用 `backend/scripts/init_db.py`——脚本在 `backend/data/init_db.py`。

### 造测试数据（登录 + 记录）
```bash
uv run python scripts/create_admin.py    # admin/admin123
uv run python scripts/seed_test_data.py  # user1~4/test1234 + 170 条记录 + 21 菜单
```

### 启动后端
```bash
cd backend
uv run python main.py    # http://localhost:8000/docs
```

### 启动前端
```bash
cd frontend
npm run dev              # http://localhost:5173
```

### 测试
```bash
cd frontend && npm run test                  # 前端 Vitest（30/30）
uv run pytest tests/b -q --ignore=tests/b/llm/test_llm_connectivity.py   # 后端 B（106 passed）
uv run python tests/b/D3/test_record.py      # 摄入记录脚本式（7/7）
uv run pytest tests/a -q --ignore=tests/a/D5/test_acceptance.py          # 后端 A
```
> ⚠️ `tests/b/llm/test_llm_connectivity.py` 与部分 A 脚本式测试是 `python xxx.py` 直接跑，不要用 pytest 收集（会报 fixture/SystemExit）。

### 类型检查
```bash
cd frontend && npx vue-tsc -b
```

## 3. 架构与关键文件

```
backend/
  main.py            # FastAPI 入口：/chat /chat/stream /profile /location /admin/*
  agent/agent.py     # LangChain Agent 编排（流式 astream_events、会话隔离）
  agent/subagent.py  # 搭配优化子 Agent（agent 即工具）
  tools/registry.py  # 工具注册中心（新增工具在此登记）
  tools/scoring.py   # 评分公式（多目标权重均值）
  tools/optimizer.py # 组合优化（背包/DP）
  tools/record.py    # 摄入记录（HITL confirm/reject）
  rag/retriever.py   # Chroma RAG（确定性哈希缓存）
  store/profile.py   # 用户画像长期记忆（营养摘要）
  middleware/        # token_counter / metrics / reply_formatter / logger
  db/db.py           # SQLite 访问 + 迁移（DB_PATH 绝对化解析）
  auth/              # JWT + PBKDF2 用户系统（/auth/*）
  mcp/               # 天气 MCP（location / weather_data / weather_http）

frontend/src/
  views/             # ChatView / TrendView / RecordsView / ProfileView / MenuView
  components/        # DishCard / MealComboCard / ProfileForm / TagInput / TodayOverview
  stores/            # chat / auth / profile（pinia）
  api/               # 后端接口封装（client.ts 统一 baseURL）
```

## 4. 数据流（推荐链路）

```
用户输入 → main.py(/chat/stream) → agent.py(astream_events)
  → 工具(registry): search / recommend / record / optimizer / weather
  → tools/scoring.py 评分 → LLM 生成理由
  → 流式 SSE 回前端（delta 逐字 + dishes 结构化 + done）
前端: dishes 事件暂存，done 后才挂载菜品卡片
```

## 5. 已知坑（改代码前必读）

1. **DB_PATH 相对路径**：`.env` 里 `DB_PATH=backend/data/canteen.db` 是相对路径，启动目录不同会错位成 `backend/backend/...` 嵌套库。`db.py` 已做绝对化，**不要自己改成别的相对路径**。
2. **.env 位置**：真实配置在 `backend/.env`（不是项目根）。`location.py`/`weather_data.py` 的 `load_dotenv` 必须指向 `backend/.env`。
3. **`backend/mcp/` 与 MCP SDK 同名**：`weather_server` 必须以脚本方式启动（`python weather_server.py`），不要 `import mcp` 顶层引冲突。
4. **远程 Ollama**：`ollama.service` 已配 `OLLAMA_NUM_PARALLEL=2`、`KV_CACHE_TYPE=q8_0`、`FLASH_ATTENTION=1`、`KEEP_ALIVE=24h`；`.env` 里 `num_predict` 限制输出防占满 slot。
5. **前端发送按钮选择器**：页面有"今日吃什么？"等多个 `el-button--primary` 快捷按钮，测试定位发送按钮须按文本过滤，不能用 `.find('button.el-button--primary')`（会点错）。
6. **密钥不入库**：真实 key 只在 `backend/.env`，`README`/`.env.example` 用假值；`.gitignore` 已含 `.env`、`*.db`、`metrics.json`、日志。
7. **`backend/data/chroma_db`** 是 RAG 向量库，重建需重新嵌入（脚本或首次调用自动建）。

## 6. 常见开发任务

### 新增一个后端工具
1. 在 `backend/tools/` 下写函数 + `@tool` 装饰器（带中文 docstring）。
2. 在 `backend/tools/registry.py` 登记。
3. 跑 `tests/b/` 对应用例或补新用例。

### 新增一道菜（数据）
1. 编辑 `backend/data/dishes.csv`（字段与表结构一致）。
2. 重跑 `uv run python data/init_db.py`（会重建库，注意会丢业务记录，仅开发用）。

### 改推荐评分
- 改 `backend/tools/scoring.py`（`_goal_weights` 多目标权重、忌口硬过滤）。
- 验证：`tests/b/D2`、`tests/a/D4/test_optimizer.py`。

### 新增页面
1. `frontend/src/views/xxx.vue` + 在 `router/index.ts` 注册。
2. API 封装放 `frontend/src/api/xxx.ts`。
3. 补 `xxx.test.ts`，跑 `npm run test`。

## 7. 部署（ginna.cn）

```bash
# 后端容器（云端 API）
cd docker
docker build -f Dockerfile.backend -t canteen-backend:1.1.0 ..
docker compose -f docker-compose.yml up -d backend
# 前端静态
cd frontend && npm run build
# 上传 dist 到 /var/www/canteen（SSH: root@ginna.cn）
```

- 部署开关：`USE_CLOUD_API=true`（`OPENAI_MODEL=qwen3.6-flash`，base `https://token.bayesdl.com/api/maas/v1`）。
- 数据卷 `canteen-data` 持久化 `canteen.db`，重建容器不丢数据。
- 详见 `docs/DEPLOY.md`（含远程 Ollama 服务器优化、常见坑）。

## 8. 验收要点（对照评分标准）

- 及格底线：Agent 链路通、≥1 自写工具、README+.env.example+5 组测试。
- 良好：≥3 工具、HITL 审批、中间件、数据清洗记录、边界处理。
- 优秀：子 Agent ✅、MCP ✅、Store 长期记忆 ✅、Token 中间件 ✅、流式+会话隔离 ✅、Skill 文档（本文件）✅、SUMMARY ✅。
