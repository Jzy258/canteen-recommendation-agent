# 食堂菜品推荐与营养分析 Agent

一款专为食堂就餐场景设计的智能助手，帮助快速、科学地选择符合个人口味与健康需求的餐食。

## 项目简介

对话式点餐参谋，核心能力：

1. **查**：查询菜品营养信息（热量、蛋白质、碳水、脂肪），数据注明参考来源
2. **荐**：按预算与营养需求推荐荤素搭配合理的一餐，并给出推荐理由（自研评分公式 + 组合优化算法）
3. **追踪**：记录多日每餐摄入（HITL 确认），按天、按周输出营养摄入趋势
4. **进阶**：天气 MCP 推荐、搭配优化子 Agent、多轮记忆、Token 中间件统计

## 团队分工

| 角色 | 范围 |
|------|------|
| A · 数据与算法 | 菜品营养库、数据清洗、SQLite schema、评分公式、组合优化 |
| B · Agent 与 LLM | LangChain Agent 编排、工具注册、RAG、LLM 适配、中间件、天气 MCP、会话 |
| C · 前端/测试/文档 | Vue3 界面、测试用例、文档整合、Docker 部署 |

详见 `docs/团队分工.md`。

## 技术栈

- 后端：FastAPI + LangChain + SQLite（本地 LLM：Ollama，可切云端 API）
- 前端：Vue3 + TypeScript + Element Plus + ECharts（Vite）
- 部署：Docker Compose（frontend + backend + ollama + mcp-weather）

## 快速开始

### Docker 一键启动（推荐演示）

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d --build
# 后端 http://localhost:8000/docs · 前端 http://localhost:8080
```

### 本地开发

```bash
# 后端（Python 3.14 + uv）
cd backend
uv sync
uv run python data/init_db.py      # 首次：建表 + 导入 100 道菜 / 多天菜单
uv run python main.py              # http://localhost:8000

# Ollama（本地 LLM）
ollama serve
ollama pull qwen2.5:7b

# 前端（Node 18+）
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

详细部署与常见坑见 `docs/DEPLOY.md`。

## 测试

```bash
# 前端单元测试（Vitest，30/30 通过）
cd frontend && npm run test

# 后端核心模块（pytest，106 passed）
uv run pytest tests/b -q --ignore=tests/b/llm/test_llm_connectivity.py

# 后端摄入记录脚本式用例（7/7 通过）
uv run python tests/b/D3/test_record.py
```

结果记录见 `tests/results/`（含 `v1.3.0-全量回归.md`）；完整测试清单见 `tests/`（A/B/C 各自目录）。

## 运行效果截图

> 待补：聊天推荐页、营养趋势页、饮食记录页、偏好设置页截图（答辩/验收用，至少一张）。
> 演示环境：本地启动后访问 `http://localhost:5173`；线上体验 `https://ginna.cn/canteen/`。

## 文档

- 需求：`docs/项目需求.md`　·　选题：`docs/项目选题.md`
- 规格：`docs/REQUIREMENTS.md`　·　设计：`docs/DESIGN.md`
- 分析：`docs/ANALYSIS.md`　·　部署：`docs/DEPLOY.md`
- 复盘：`docs/总结/SUMMARY.md`　·　技能：`docs/SKILL.md`　·　评分：`docs/评分标准.md`
- 接口：`docs/BC-API文档.md`（B→C）· `docs/AB-接口合约.md`（A→B）
- 算法：`docs/评分公式说明.md`　·　选型：`docs/技术选型.md`
- 分工：`docs/团队分工.md`　·　规范：`docs/版本管理规范.md`

## 配置

复制 `.env.example` 为 `backend/.env` 填写（不提交真实密钥）。核心变量：`OLLAMA_BASE_URL`、`OLLAMA_MODEL`、`DB_PATH`、天气 `WEATHER_API_KEY`（可选）。