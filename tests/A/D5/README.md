# D5 — 边界场景测试数据（供 C 测试）

> 用途：配合 C 的测试，覆盖**边界 case**（预算过低、无匹配菜品、热量上限过低、
> 无画像、异常输入等）。正常场景数据见 `tests/A/D3/seed_meal_records.csv`。

## 文件

| 文件 | 说明 |
|------|------|
| `edge_scenarios.csv` | 边界场景用例表（输入 + 预期行为） |
| `edge_meal_records.csv` | 边界摄入记录（含部分待确认、半份量） |
| `edge_scores.csv` | 评分边界断言（含超预算/无偏好/极端目标） |

---

## 1. edge_scenarios.csv — 边界用例表

| 场景 | 输入 | 预期行为 |
|------|------|----------|
| 预算过低 | `recommend(budget=1)` | 返回全部价格 ≤1 的菜品（米饭/馒头/花卷/西瓜/柠檬水），无报错 |
| 预算为0 | `recommend(budget=0)` | 无预算约束，返回全部菜品 |
| 无匹配菜品 | `search_dish(keyword="佛跳墙")` | 返回空列表 `[]` |
| 超热量上限 | `optimize_meal(budget=20, calorie_limit=300)` | 可能 balance_ok=False 并给出原因，不崩溃 |
| 热量上限为0 | `optimize_meal(budget=20, calorie_limit=0)` | 返回空 + reason |
| 未知菜品ID | `record_meal(dish_id=999)` | 外键约束拒绝（IntegrityError） |
| 空偏好 | `recommend(preferences="")` | 偏好取中性，正常返回 |
| 极端目标 | `recommend(health_goals="控油")` | 素菜得分上升，正常返回 |

---

## 2. edge_meal_records.csv — 边界摄入记录

覆盖：部分待确认、半份量、多天零散记录（供 HITL 与聚合边界测试）

```csv
date,meal_time,dish_id,portion,confirmed
2026-08-10,lunch,1,0.5,1        # 半份红烧肉 250kcal
2026-08-10,lunch,37,1,1         # 米饭
2026-08-10,dinner,17,1,0        # 待确认（不应进入聚合）
2026-08-11,breakfast,44,1,0     # 待确认
2026-08-11,lunch,6,1,1          # 土豆烧牛肉
2026-08-13,dinner,3,1,1         # 隔天记录（趋势图应补零）
```

**断言参考**：
- `get_day_total("2026-08-10")["total_calories"]` = 250 + 200 = **450.0**
- `get_pending_records()` 应返回 **2 条**（8-10 dinner + 8-11 breakfast）
- `get_weekly_trend(end_date="2026-08-13", days=7)` 中 8-12 应为 **0**

---

## 3. edge_scores.csv — 评分边界断言

| 用例 | 输入 | 期望 |
|------|------|------|
| 超预算 | `score_dish(红烧肉, budget=10)` | S_budget=0.9（12元 vs 预算10） |
| 双倍超预算 | `score_dish(葱爆羊肉15元, budget=10)` | S_budget=0.75 |
| 无预算 | `score_dish(红烧肉, budget=0)` | S_budget=1.0 |
| 无偏好 | `preference_score(红烧肉, 无偏好)` | 0.5（中性） |
| 控油偏好 | `preference_score(清炒小白菜, 控油)` | 0.7（素菜加分） |
| 完美营养 | 荤菜 350/22/15/20 | nutrition_score ≈ 1.0 |
| 减脂荤菜 | `preference_score(红烧肉, 减脂)` | 0.42（0.6×0.5无偏好口味 + 0.4×0.3荤菜扣分） |

---

## 4. 与接口的对应（C 可直接断言）

```python
from db import get_db
from tools.scoring import score_dish, budget_score
from tools.optimizer import optimize_meal

db = get_db()

# 预算过低
db.search_dishes(max_price=1)                    # 米饭/馒头/花卷等

# 无匹配
db.search_dishes(keyword="佛跳墙") == []

# 超热量上限（balance_ok=False 不崩溃）
optimize_meal(db.get_all_dishes(), 20, 300)["balance_ok"]  # False 或 True 均可，不抛异常

# 评分边界
budget_score(12, 10)   # 0.9
budget_score(12, 0)    # 1.0
```