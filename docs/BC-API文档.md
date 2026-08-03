# B → C API 文档

> 版本：v1.1　|　日期：2026-08-03　|　状态：D1~D4 可用
> 对应后端：`backend/main.py`（FastAPI），端口默认 `8000`

---

## 1. 基本信息

| 项目 | 值 |
|------|-----|
| 基础地址 | `http://localhost:8000` |
| 响应格式 | `application/json` |
| CORS | 全开（`*`），前端开发无需代理 |
| 交互式文档 | `http://localhost:8000/docs`（Swagger UI） |

---

## 2. 端点

### 2.1 健康检查

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

### 2.2 聊天对话

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
| 500 | LLM 连接失败等 | `{"reply": "Sorry, an error occurred: ...", "session_id": "xxx"}` |

---

## 3. 前端对接建议

### 3.1 交互流程

```
用户输入 → POST /chat → 展示 reply → 保存 session_id → 下一轮传入
```

### 3.2 会话管理

- 首次对话不传 `session_id`，后端生成并返回，前端保存
- 后续对话传入同一 `session_id` 保持会话连续性
- 新会话传新 `session_id` 或留空触发新会话

### 3.3 用户输入场景（当前可用）

| 场景 | 示例 message |
|------|-------------|
| 查全部菜品 | `"有什么菜？"` |
| 查具体菜品 | `"查一下红烧肉"` |
| 关键词搜索 | `"鸡肉相关的菜"` |
| 按分类 | `"有哪些素菜？"` |
| 价格查询 | `"5块以下的菜"` |
| 按预算推荐 | `"10块钱预算推荐几个菜"` |
| 按健康目标推荐 | `"推荐高蛋白的菜"` |
| 组合优化一餐 | `"预算20元、热量800卡以内配一餐"` |
| 记录摄入 | `"帮我记录今天午餐吃了红烧肉"` |
| 查看趋势 | `"最近7天营养摄入趋势"` |

---

## 4. 数据模型

### 菜品字段（`reply` 中可能返回）

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

---

## 5. 启动方式

```bash
cd backend
uv run python main.py
# 访问 http://localhost:8000/docs 查看交互式文档
```