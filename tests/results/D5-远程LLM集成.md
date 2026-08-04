# C 测试结果记录（D5 · 远程 LLM 集成）

> 日期：2026-08-04　|　远程服务器：119.45.135.201:11434（Ubuntu，4核/15G，CPU 推理）

---

## 远程 LLM / Embedding 服务器部署

| 项 | 值 |
|----|-----|
| Ollama | v0.32.5（systemd 服务，监听 0.0.0.0:11434） |
| LLM | `qwen2.5:7b`（Q4_K_M，7.6B 参数，支持 tools；`qwen3.5:7b` 不存在故替代） |
| Embedding | `bge-m3`（1024 维，8192 context） |
| 外网可达 | `curl http://119.45.135.201:11434/api/version` → `{"version":"0.32.5"}` |

## 端到端验证（本地后端 → 远程 LLM）

| 场景 | 请求 | 结果 | 状态 |
|------|------|------|------|
| 对话/推荐 | `"10块钱预算推荐几个菜"` | 5 道推荐 + 价格/理由，977 字 | PASS |
| 推荐+理由 | `"推荐清淡的高蛋白菜"` | 5 道清淡高蛋白菜 + 理由，体现偏好 | PASS |
| RAG 语义检索 | `"我想吃麻辣的水煮菜"` | 命中"麻辣水煮鱼/水煮牛肉"（bge-m3 向量） | PASS |
| 流式 SSE | `/chat/stream` | session→53×delta→done 顺序正确 | PASS |
| 健康检查 | `GET /health` | ok | PASS |

## 集成测试（tests/c/D5/test_integration.py，需后端运行）4/4

- 趋势接口 `/trend`（7 天连续补零，字段完整）
- 趋势默认参数
- 流式 SSE 三段事件
- 中间件 `/metrics`

## 说明

- 后端配置：`backend/.env` 指向 `OLLAMA_BASE_URL=http://119.45.135.201:11434`，
  `OLLAMA_EMBED_MODEL=bge-m3`（RAG 走 bge-m3 向量）。
- 腾讯云安全组已放行入站 TCP 11434。
- CPU 推理每轮约 5~30s，演示注意等待。
