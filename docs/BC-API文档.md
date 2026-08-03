# B → C API 文档

> 版本：v2.0　|　日期：2026-08-03　|　状态：D1~D7 全部可用
> 对应后端：`backend/main.py`（FastAPI v0.6.0），端口默认 `8000`
> 交互式文档：`http://localhost:8000/docs`（Swagger UI，可直接调试）

---

## 1. 基本信息

| 项目 | 值 |
|------|-----|
| 基础地址 | `http://localhost:8000` |
| 响应格式 | `application/json` |
| CORS | 全开（`*`），前端开发无需代理 |
| 交互式文档 | `http://localhost:8000/docs` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |
| 项目版本 | `0.6.0`（SemVer） |

---

## 2. 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/metrics` | 中间件统计（请求数/耗时/Token） |
| POST | `/chat` | 对话（普通 JSON 返回） |
| POST | `/chat/stream` | 对话（SSE 流式返回） |

---

## 3. 端点详情

### 3.1 健康检查

```
GET /health
```

**响应 200**

```json
{
  "status": "ok"
}
```

---

### 3.2 中间件统计

```
GET /metrics
```

**响应 200**

| 字段 | 类型 | 说明 |
|------|------|------|
| `requests` | int | 累计请求数 |
| `errors` | int | 累计错误数 |
| `avg_time_ms` | float | 平均耗时（ms） |
| `total_time_ms` | float | 总耗时（ms） |
| `total_tokens` | int | 累计 Token 用量（tiktoken 精确计数） |
| `by_path` | object | 各路径请求数分布 |

```json
{
  "requests": 12,
  "errors": 0,
  "avg_time_ms": 82.4,
  "total_time_ms": 988.8,
  "total_tokens": 1532,
  "by_path": {"/health": 8, "/chat": 4}
}
```

---

### 3.3 聊天对话（普通）

```
POST /chat
Content-Type: application/json
```

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | string | 是 | 用户输入文本，不能为空 |
| `session_id` | string | 否 | 会话标识，不传则自动生成 |

**请求示例**

```json
{
  "message": "有什么菜？",
  "session_id": "user-abc-123"
}
```

**响应 200**

| 字段 | 类型 | 说明 |
|------|------|------|
| `reply` | string | LLM 回复内容 |
| `session_id` | string | 会话 ID（传入则原值返回，不传则新生成） |

```json
{
  "reply": "食堂现有以下菜品：红烧肉（500kcal，12元）、宫保鸡丁（350kcal，10元）……",
  "session_id": "user-abc-123"
}
```

**错误响应**

| 状态码 | 场景 | 示例 |
|--------|------|------|
| 400 | `message` 为空 | `{"detail": "Message cannot be empty"}` |
| 200 | LLM 内部异常 | `{"reply": "抱歉，系统处理出错，请稍后再试或换一种问法。", "session_id": "xxx"}` |

> LLM 故障时返回**友好中文提示**（不抛 traceback，不泄露内部细节）。

---

### 3.4 聊天对话（流式 SSE）

```
POST /chat/stream
Content-Type: application/json
Accept: text/event-stream
```

**请求参数**（同 `/chat`）：`message`（必填）、`session_id`（可选）

**响应 200**：`text/event-stream`，按以下事件序列输出：

| 事件 | type | 内容 | 说明 |
|------|------|------|------|
| 1 | `session` | `{"session_id": "..."}` | 会话元数据（最先） |
| 2..n | `delta` | `{"content": "..."}` | 回复增量（每次约 4 字符） |
| 最后 | `done` | `{}` | 流结束标记 |

**原始 SSE 示例**

```
data: {"type": "session", "session_id": "user-abc-123"}

data: {"type": "delta", "content": "食堂现有"}

data: {"type": "delta", "content": "以下菜品"}

data: {"type": "done"}
```

**前端解析建议（EventSource 不可用于 POST，用 fetch + ReadableStream）**

```ts
const res = await fetch('http://localhost:8000/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: '有什么菜？', session_id: 'user-abc-123' })
});
const reader = res.body.getReader();
const decoder = new TextDecoder();
let reply = '';
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value, { stream: true });
  for (const line of text.split('\n')) {
    if (!line.startsWith('data: ')) continue;
    const evt = JSON.parse(line.slice(6));
    if (evt.type === 'delta') { reply += evt.content; updateUI(reply); }
    if (evt.type === 'done') { onDone(); }
  }
}
```

---

## 4. 前端对接建议

### 4.1 交互流程

```
用户输入 → POST /chat 或 /chat/stream → 展示 reply → 保存 session_id → 下一轮传入
```

### 4.2 会话管理

- 首次对话不传 `session_id`，后端生成并返回，前端保存
- 后续对话传入同一 `session_id` 保持上下文（多轮记忆）
- 新会话传新 `session_id` 或留空
- 会话有 TTL（60 分钟未活动自动过期）与数量上限（LRU 淘汰），前端无需处理

### 4.3 用户输入场景

| 场景 | 示例 message |
|------|-------------|
| 查全部菜品 | `"有什么菜？"` |
| 查具体菜品 | `"查一下红烧肉"` |
| 关键词搜索 | `"鸡肉相关的菜"` |
| 近似/语义检索 | `"辣的荤菜"` |
| 按分类 | `"有哪些素菜？"` |
| 价格查询 | `"5块以下的菜"` |
| 按预算推荐 | `"10块钱预算推荐几个菜"` |
| 按健康目标推荐 | `"推荐高蛋白的菜"` |
| 组合优化一餐 | `"预算20元、热量800卡以内配一餐"` |
| 按天气推荐 | `"今天天气适合吃什么？"` |
| 记录摄入 | `"帮我记录今天午餐吃了红烧肉"` |
| 确认摄入 | `"确认记录"` |
| 查看趋势 | `"最近7天营养摄入趋势"` |
| 设置偏好 | `"我的预算是15元，喜欢辣的"` |

---

## 5. 数据模型

### 5.1 菜品（对话中可能返回）

| 字段 | 类型 | 示例 |
|------|------|------|
| name | string | `"红烧肉"` |
| calories | float | `500.0` |
| protein | float | `20.0` |
| carbs | float | `10.0` |
| fat | float | `35.0` |
| price | float | `12.0` |
| category | string | `"荤菜"` |
| flavor_tags | string | `"咸,甜"` |
| source | string | `"中国食物成分表第6版"` |

### 5.2 摄入记录（趋势/汇总相关回复）

| 字段 | 类型 | 说明 |
|------|------|------|
| date | string | 日期 `"2026-08-03"` |
| meal_time | string | 餐次 lunch/dinner 等 |
| total_calories | float | 总热量 kcal |
| total_protein | float | 总蛋白质 g |
| total_carbs | float | 总碳水 g |
| total_fat | float | 总脂肪 g |
| dish_count | int | 菜品数 |

---

## 6. 启动方式

```bash
cd backend
uv run python main.py
# 交互式文档: http://localhost:8000/docs
```

> Docker 部署见 `docs/DEPLOY.md`（`docker compose -f docker/docker-compose.yml up -d`）。
