# A · 数据与算法 — 工作计划

> 角色：A · 数据与算法
> 负责模块：`backend/data/`、`backend/db/`、`backend/tools/scoring.py`、`backend/tools/optimizer.py`

---

## 第一阶段：基础数据建设（D1–D2）— 及格保底

**目标**：搭建完整菜品库与菜单数据，确保 Agent 链路有数据可查。

### D1 — 建表 + 灌 30 道菜

| 序号 | 任务 | 产出文件 | 说明 |
|------|------|----------|------|
| 1.1 | 设计 SQLite schema | `backend/db/schema.sql` | 4 表：`dish`、`menu`、`meal_record`、`user_profile`，字段类型、主外键、索引 |
| 1.2 | 实现数据访问层 | `backend/db/db.py` | 连接管理、CRUD 基础函数，预留可换 MySQL 的接口抽象 |
| 1.3 | 采集 50 道菜品营养数据 | `backend/data/dishes.csv` | 字段：名称、热量、蛋白质、碳水、脂肪、价格、口味标签、荤素类别、参考来源 |
| 1.4 | 编写初始化脚本 | `backend/data/init_db.py` | 建表 + 导入 50 道菜到 SQLite |
| 1.5 | 验证数据可被 B 的 search 工具查询 | 联调确认 | 与 B 确认 `db.py` 接口签名，确保 B 能直接调用 |

### D2 — 补 50+ 道菜 + 菜单 + 清洗记录

| 序号 | 任务 | 产出文件 | 说明 |
|------|------|----------|------|
| 2.1 | 扩展到 50+ 道菜品 | `backend/data/dishes.csv` | 覆盖荤、素、汤、主食、水果等类别 |
| 2.2 | 采集 5天×3餐 菜单 | `backend/data/menu.csv` | 对应食堂实际供餐场景，结构化入库 |
| 2.3 | 编写清洗脚本 | `backend/data/clean.py` | 去重、统一单位（g/kcal）、缺失值填充策略 |
| 2.4 | 清洗记录文档 | `backend/data/cleaning_log.md` | 记录清洗过程、数据来源、处理方式，作为答辩依据 |
| 2.5 | 重跑初始化脚本 | 更新 `canteen.db` | 确保 50+ 道菜 + 菜单完整入库 |

### 交付物（D1–D2 验收）
- `backend/db/schema.sql` ✅
- `backend/db/db.py` ✅
- `backend/data/dishes.csv`（50+ 条）✅
- `backend/data/menu.csv`（5天×3餐）✅
- `backend/data/clean.py` ✅
- `backend/data/cleaning_log.md` ✅
- `backend/data/init_db.py` ✅

---

## 第二阶段：摄入追踪（D3）— 中等

**目标**：支撑多日饮食追踪功能，提供摄入记录与聚合查询能力。

| 序号 | 任务 | 产出文件 | 说明 |
|------|------|----------|------|
| 3.1 | 完善 `meal_record` 表聚合查询 | `backend/db/db.py` | 按天/按周聚合：总热量、蛋白质、碳水、脂肪 |
| 3.2 | 编写摄入记录数据访问函数 | `backend/db/db.py` | `add_meal_record()`、`get_daily_nutrition()`、`get_weekly_trend()` |
| 3.3 | 配合 B 联调 | 接口确认 | 确保 B 的 `record.py` 工具能正确调用聚合函数 |
| 3.4 | 提供测试数据 | 补充测试数据 | 为 C 的测试提供 3-5 天模拟摄入记录 |

### 交付物（D3 验收）
- `db.py` 新增聚合查询函数 ✅（get_daily_nutrition / get_day_total / get_weekly_nutrition / get_weekly_summary / get_weekly_trend）
- 联调通过 ✅（tests/A/D3/test_record_integration.py 模拟 record.py 8 场景全通过，接线示例已写入 AB-接口合约）
- 测试数据 ✅（tests/A/D3/seed_meal_records.csv 5天55条 + load_seed_data.py + README，含每日/周营养参考值）

---

## 第三阶段：算法核心 + 审批流（D4–D5）— 良好

**目标**：实现自研推荐评分公式、组合优化算法，以及 HITL 审批流的数据支撑。

### D4 — 组合优化算法

| 序号 | 任务 | 产出文件 | 说明 |
|------|------|----------|------|
| 4.1 | 设计推荐评分公式 | `backend/tools/scoring.py` | 预算约束（价格 ≤ 预算）、营养均衡（热量/蛋白质/碳/水/脂肪偏离度）、偏好权重（口味、荤素），系数写入文档 |
| 4.2 | 实现评分函数 | `backend/tools/scoring.py` | `score_dish(dish, user_profile)` 返回评分值 |
| 4.3 | 实现组合优化算法 | `backend/tools/optimizer.py` | 给定预算+热量上限，用背包/DP 求最优一餐搭配（荤素搭配合理） |
| 4.4 | 评分公式文档 | `docs/评分公式说明.md` | 系数含义、计算方式、调整策略，作为答辩依据 |
| 4.5 | 单元测试 | 本地验证 | 验证评分函数和优化算法的正确性 |

### D5 — HITL 审批流

| 序号 | 任务 | 产出文件 | 说明 |
|------|------|----------|------|
| 5.1 | 实现 HITL 审批数据接口 | `backend/db/db.py` | 提供"待确认记录"缓存、"确认写入"、"拒绝丢弃"接口 |
| 5.2 | 完善 `user_profile` 更新逻辑 | `backend/db/db.py` | 每餐确认后更新用户历史营养汇总 |
| 5.3 | 配合 B 联调审批流 | 接口确认 | 确保 B 的 Agent 流程能正确调用 HITL 接口 |
| 5.4 | 配合 C 补充测试数据 | 多样化场景数据 | 边界 case：预算过低、无匹配菜品等 |

### 交付物（D4–D5 验收）
- `backend/tools/scoring.py` ✅
- `backend/tools/optimizer.py` ✅
- `docs/评分公式说明.md` ✅
- `db.py` HITL 接口函数 ✅
- 联调通过 ✅

---

## 第四阶段：亮点扩展（D6）— 优秀

**目标**：配合天气 MCP 提供天气相关的菜品推荐数据支撑。

| 序号 | 任务 | 产出文件 | 说明 |
|------|------|----------|------|
| 6.1 | 维护天气-菜品标签映射 | `backend/data/weather_food_map.csv` | 天冷 → 热汤面/炖菜/热饮，天热 → 凉菜/清淡/水果 |
| 6.2 | 提供天气标签查询函数 | `backend/db/db.py` | `get_dishes_by_weather_tag(weather_type)` |
| 6.3 | 配合 B 联调天气 MCP 链路 | 接口确认 | 确保 B 的天气 MCP 能调用菜品标签筛选 |
| 6.4 | 配合 C 提供演示数据 | 演示场景数据 | 天气推荐演示场景的菜品数据准备 |

### 交付物（D6 验收）
- `backend/data/weather_food_map.csv` ✅
- `db.py` 天气标签查询函数 ✅
- 联调通过 ✅

---

## 第五阶段：收尾（D7）— 修 bug + 配合答辩

| 序号 | 任务 | 说明 |
|------|------|------|
| 7.1 | 修复 Al 各模块 bug | 数据边界、异常输入、空结果处理 |
| 7.2 | 配合 B 修 Agent 链路问题 | 数据相关的集成问题 |
| 7.3 | 配合 C 完善文档 | 提供评分公式、数据清洗等素材 |
| 7.4 | 答辩准备 | 演示数据准备、Q&A 准备 |

---

## 关键依赖与风险

| 依赖/风险 | 说明 | 应对 |
|-----------|------|------|
| 营养数据来源 | 需从《中国食物成分表》/公开数据采集 | D1 前确定数据源，批量采集 |
| B 依赖 A 的 schema | B 的 store/record 工具依赖 A 的 db schema | D1 必须定稿 schema，改动即时通知 |
| 评分公式系数 | 需要合理设计，避免推荐结果不合理 | D4 前与团队讨论，参考营养学常识 |
| 数据清洗 | 数据质量直接影响演示效果 | 清洗过程记录在 `cleaning_log.md` 作为答辩依据 |