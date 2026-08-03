# A → B 联调确认：db 接口合约

> 更新日期：2026-08-02
> B 的 tools/search.py、tools/record.py 通过以下接口访问数据库，无需直接操作 SQLite。
> 联调状态：record.py 调用模式已由 `tests/A/D3/test_record_integration.py` 模拟验证通过。

---

## 1. 调用方式

```python
from db import get_db

db = get_db()          # 单例，全局共享
results = db.search_dishes(keyword="红烧肉")
```

## 2. 接口列表

### 菜品检索（B 的 search 工具使用）

| 接口 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `search_dishes(keyword, category, max_price)` | 全部可选参数 | `list[dict]` | 关键词 LIKE 模糊搜索 + 分类/价格筛选，全空则返回全部 |
| `get_dish_by_id(dish_id)` | `int` | `dict \| None` | 精确 ID 查询 |
| `get_dish_by_name(name)` | `str` | `dict \| None` | 精确名称匹配 |
| `get_all_dishes()` | 无 | `list[dict]` | 全部菜品，按 id 排序 |

### 菜单查询（B 的 search 工具使用）

| 接口 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_menu_by_date(date)` | `"2026-08-03"` | `list[dict]` | 某天全部餐次菜单（含菜品营养） |
| `get_menu_by_date_range(start, end)` | 起止日期 | `list[dict]` | 日期范围菜单 |
| `get_weekly_menu()` | 无 | `list[dict]` | 全部菜单 |
| `get_dishes_for_menu(date, meal_time)` | 日期+餐次 | `list[dict]` | 某餐次的具体菜品列表 |

### 摄入记录（B 的 record 工具使用）

| 接口 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `add_meal_record(date, meal_time, dish_id, portion)` | 必填 | `int` (record_id) | 新增待确认记录 |
| `confirm_meal_record(record_id)` | `int` | `bool` | 用户确认 → `confirmed=1`，并刷新 user_profile 营养汇总 |
| `reject_meal_record(record_id)` | `int` | `bool` | 用户拒绝 → `confirmed=-1` |
| `confirm_records(record_ids)` | `list[int]` | `int` | 批量确认，返回实际确认条数 |
| `reject_records(record_ids)` | `list[int]` | `int` | 批量拒绝，返回实际拒绝条数 |
| `get_pending_records()` | 无 | `list[dict]` | 全部待确认记录（含菜品名+营养） |
| `get_pending_records_by_date(date, meal_time)` | 日期，餐次可选 | `list[dict]` | 按日期/日期+餐次过滤待确认记录 |
| `get_pending_record(record_id)` | `int` | `dict \| None` | 查询单条待确认记录 |
| `get_records_by_date(date)` | 日期 | `list[dict]` | 已确认的某天记录 |
| `get_daily_nutrition(date)` | 日期 | `list[dict]` | 按天+餐次汇总营养（视图 v_daily_nutrition） |
| `get_day_total(date)` | 日期 | `dict \| None` | 全天营养合计（视图 v_day_total） |
| `get_weekly_nutrition(start, end)` | 日期范围 | `list[dict]` | 按天汇总营养（视图 v_weekly_nutrition） |
| `get_weekly_summary(start, end)` | 日期范围 | `dict \| None` | 周营养合计 + 天数/菜品数（视图 v_week_summary） |
| `get_weekly_trend(end_date, days)` | `end_date` 默认今天，`days` 默认7 | `list[dict]` | 连续 N 天每日营养合计，缺失日期补零（供趋势图） |

> **HITL 流程**：`add_meal_record` 写入 `confirmed=0`（待确认）→ 展示给用户 →
> `confirm_records`/`reject_records` 批量审批 → 确认后自动刷新 `user_profile.nutrition_summary`
> （供 Store 长期记忆）。测试：`tests/A/D5/test_all.py` 全部通过。
>
> **联调状态（B 审批流）**：B 的 `tools/record.py` + `agent.py` 已注册
> `record_meal`/`confirm_record`/`reject_record`/`get_pending_records`/`get_daily_intake` 等工具。
> `tests/A/D5/test_hitl_integration.py` 按 B 的调用模式模拟完整审批流全部通过：
> 记录 → 待确认展示 → 确认/拒绝 → 营养聚合（被拒记录不计入）→ user_profile 汇总刷新。

### record.py 工具接线示例（已联调验证）

B 的 `tools/record.py` 按 `search.py` 同款模式编写即可：

```python
from langchain_core.tools import tool
from db import get_db

db = get_db()


@tool
def record_meal(date: str, meal_time: str, dish_id: int, portion: float = 1.0) -> int:
    """Record a meal intake (pending confirmation)."""
    return db.add_meal_record(date, meal_time, dish_id, portion)


@tool
def confirm_record(record_id: int) -> bool:
    """Confirm a pending meal record."""
    return db.confirm_meal_record(record_id)


@tool
def get_daily_intake(date: str) -> list[dict]:
    """Get daily nutrition breakdown by meal_time."""
    return db.get_daily_nutrition(date)


@tool
def get_day_total(date: str) -> dict:
    """Get whole-day nutrition total."""
    return db.get_day_total(date)


@tool
def get_weekly_trend(end_date: str = "", days: int = 7) -> list[dict]:
    """Get daily nutrition totals for the last N days."""
    return db.get_weekly_trend(end_date=end_date, days=days)
```

> 联调确认：`tests/A/D3/test_record_integration.py` 用上述模式模拟 8 个场景全部通过，覆盖「记录→确认→按餐次/全天/周趋势/周汇总」全链路。

### 用户画像（B 的 store 工具使用）

| 接口 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_user_profile()` | 无 | `dict \| None` | 获取最近一条用户画像 |
| `upsert_user_profile(budget, flavor_preferences, ...)` | 全部可选 | `int` (id) | 有则更新，无则插入 |
| `update_nutrition_summary(summary_json)` | JSON str | `bool` | 更新历史营养汇总 |

## 3. 返回字段格式

每条 dish 记录包含：

```
{
    "id": 1,                    # int
    "name": "红烧肉",            # str
    "calories": 500.0,          # float
    "protein": 20.0,            # float
    "carbs": 10.0,              # float
    "fat": 35.0,                # float
    "price": 12.0,              # float
    "category": "荤菜",          # str
    "flavor_tags": "咸,甜",      # str
    "source": "中国食物成分表第6版", # str
    "created_at": "2026-08-01 ..."  # str
}
```

## 4. 验证结果

22 项测试全部通过，覆盖：
- 关键词模糊搜索（含/不包含）
- 分类筛选、价格筛选、组合筛选
- ID/名称精确查询（存在/不存在）
- 全部菜品查询
- 返回字段完整性及类型
- 菜单查询（空数据边界）
- 摄入记录增/改/查
- 用户画像 upsert
