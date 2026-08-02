# D3 — 模拟摄入数据（供 C 测试）

## 文件说明

| 文件 | 用途 |
|------|------|
| `seed_meal_records.csv` | 5天×3餐 模拟摄入记录，共55条，全部已确认 |
| `load_seed_data.py` | 导入脚本，自动建表+导入菜品库+导入摄入记录 |

## seed_meal_records.csv 格式

```
date,meal_time,dish_id,portion,confirmed
2026-08-03,breakfast,43,1,1
...
```

- `date`：`2026-08-03` ~ `2026-08-07`（周一到周五）
- `meal_time`：`breakfast` / `lunch` / `dinner`
- `dish_id`：对应 `backend/data/dishes.csv`（1–54）
- `portion`：份量系数（全部为 1）
- `confirmed`：HITL 状态（全部为 1=已确认）

## 数据分布

| 日期 | 早餐 | 午餐 | 晚餐 |
|------|------|------|------|
| 08-03 | 3 道 | 4 道 | 4 道 |
| 08-04 | 3 道 | 4 道 | 4 道 |
| 08-05 | 3 道 | 4 道 | 4 道 |
| 08-06 | 3 道 | 4 道 | 4 道 |
| 08-07 | 3 道 | 4 道 | 4 道 |

## 每日营养（可用于断言）

| 日期 | 热量(kcal) | 蛋白质(g) | 碳水(g) | 脂肪(g) |
|------|-----------|-----------|---------|---------|
| 08-03 | 2030.0 | 75.3 | 252.0 | 71.2 |
| 08-04 | 1930.0 | 88.2 | 252.0 | 65.0 |
| 08-05 | 2035.0 | 91.0 | 238.0 | 79.0 |
| 08-06 | 1950.0 | 96.5 | 220.0 | 75.4 |
| 08-07 | 1840.0 | 72.8 | 244.0 | 66.7 |
| **周汇总** | **9785.0** | **423.8** | **1206.0** | **357.3** |

## 使用方法

```bash
# 导入到临时数据库并打印汇总（验证用）
uv run --directory "D:\canteen recommendation agent" python tests/A/D3/load_seed_data.py

# 导入到指定数据库文件（如 C 的测试库）
uv run --directory "D:\canteen recommendation agent" python tests/A/D3/load_seed_data.py path/to/test.db
```

## 与接口的对应

导入后可直接用 A 提供的聚合接口断言：

```python
from db import get_db
db = get_db()

db.get_day_total("2026-08-03")["total_calories"]       # 2030.0
db.get_weekly_summary("2026-08-01", "2026-08-31")["total_calories"]  # 9785.0
db.get_weekly_trend(end_date="2026-08-07", days=7)     # 7天趋势（补零）
```
