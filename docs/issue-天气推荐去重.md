# [Issue] 天气推荐功能去重：请 A 评估移除 `recommend_by_weather` 或改为复用 B 的链路

> 发起人：B（Agent/LLM）　|　日期：2026-08-03
> 关联提交：`45ec8f9`（B D6）、`3769099`（A D6）

---

## 一、背景

D6 阶段 A 与 B 各自实现了天气推荐功能，出现**功能重复**：

| 实现 | 路径 | 输入 | 输出 |
|------|------|------|------|
| **B（保留）** | `mcp/weather_tool.py` → `get_weather_recommendation` | 城市名 | 实时天气 + 推荐方向 + 候选菜品 |
| A | `tools/weather.py` → `recommend_by_weather` | weather_type | 按天气类型查菜品列表 |

B 的 `get_weather_recommendation` 已经完成**完整链路**：
`城市 → 高德真实天气(含 adcode 缓存) → 天气类型 → 调 db.get_dishes_by_weather_tag 查菜 → 输出方向+菜品`。

A 的 `recommend_by_weather` 只做了其中"按天气类型查菜"这一段，与 B 内部逻辑重叠。

## 二、去重建议（请 A 二选一）

### 方案 1（推荐）：A 移除 `recommend_by_weather` @tool
- 理由：B 的 `get_weather_recommendation` 已注册进 agent（工具总数 21），完整覆盖天气推荐场景；
  agent 不需要两个都能查天气菜品的工具。
- 保留项：`weather_food_map.csv` 与 `db.get_dishes_by_weather_tag` **继续保留**（B 的工具依赖它们做标签映射，A 已从 CSV 读取，很有价值）。
- 需处理：
  - 删除 `backend/tools/weather.py` 或将其标注 deprecated
  - `tests/A/D6/test_all.py` 第 5 段对 `recommend_by_weather` 的断言改为对 `get_weather_recommendation` 的联调断言

### 方案 2（备选）：保留 `recommend_by_weather` 但 A 与 B 明确分工
- `recommend_by_weather` 只做"给定 weather_type 查菜"（纯数据查询，无天气源依赖）；
- B 的 `get_weather_recommendation` 做"城市→天气→推荐"完整链路，内部调 `db.get_dishes_by_weather_tag`。
- 需在 AB-接口合约注明两工具边界，避免 agent 同时拥有语义重复的工具。

## 三、B 已做的对齐

- `mcp/weather_tool.py`：已把 `get_db()` 延迟到函数内调用（对齐 A D6 的测试隔离修复），
  并已注册进 agent。
- 请求 A 确认方案后，B 同步更新 `docs/BC-API文档.md` 的天气场景说明。

## 四、验收

- [ ] A 确认方案 1 或方案 2
- [ ] agent 工具列表中天气推荐工具不再重复
- [ ] 全量测试通过（B 侧 D1~D6 共 66 项）
