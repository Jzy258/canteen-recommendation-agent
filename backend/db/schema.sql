-- ============================================================
-- 食堂菜品推荐与营养分析 Agent — SQLite Schema
-- 版本：v1.3（历史对话：chat_session/chat_message 表）
-- 所有者：A · 数据与算法
-- 说明：本 schema 为唯一来源，B 的 store/record 工具只读此 schema
-- ============================================================

-- 0. app_user — 用户账号（v1.1 新增）
CREATE TABLE IF NOT EXISTS app_user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,               -- 登录名（唯一）
    password_hash TEXT    NOT NULL,                      -- 密码哈希（PBKDF2-SHA256，salt 内嵌）
    role          TEXT    NOT NULL DEFAULT 'user'        -- 角色：admin / user
                         CHECK (role IN ('admin','user')),
    display_name  TEXT    DEFAULT '',                    -- 昵称
    status        INTEGER NOT NULL DEFAULT 1,            -- 1=启用 0=禁用
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    last_login_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_app_user_username ON app_user(username);

-- 1. dish — 菜品库
CREATE TABLE IF NOT EXISTS dish (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,              -- 菜品名称
    calories        REAL    NOT NULL,                     -- 热量 (kcal/份)
    protein         REAL    NOT NULL,                     -- 蛋白质 (g/份)
    carbs           REAL    NOT NULL,                     -- 碳水化合物 (g/份)
    fat             REAL    NOT NULL,                     -- 脂肪 (g/份)
    price           REAL    NOT NULL,                     -- 价格 (元)
    category        TEXT    NOT NULL,                     -- 类别：荤菜/素菜/汤/主食/水果/饮品
    flavor_tags     TEXT    DEFAULT '',                   -- 口味标签，逗号分隔，如 "辣,酸甜"
    serving_grams   REAL    DEFAULT 150,                  -- v1.2 标准份量克数（一份多少克）
    source          TEXT    NOT NULL,                     -- 参考来源，如 "中国食物成分表第6版"
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_dish_category ON dish(category);
CREATE INDEX IF NOT EXISTS idx_dish_price   ON dish(price);
CREATE INDEX IF NOT EXISTS idx_dish_name    ON dish(name);


-- 2. menu — 每日菜单（5天×3餐）
CREATE TABLE IF NOT EXISTS menu (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,                     -- 日期，如 "2026-08-03"
    meal_time       TEXT    NOT NULL,                     -- 餐次：breakfast / lunch / dinner
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE(date, meal_time)
);

CREATE INDEX IF NOT EXISTS idx_menu_date ON menu(date);


-- 3. menu_item — 菜单与菜品的多对多关联
CREATE TABLE IF NOT EXISTS menu_item (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id         INTEGER NOT NULL REFERENCES menu(id) ON DELETE CASCADE,
    dish_id         INTEGER NOT NULL REFERENCES dish(id) ON DELETE CASCADE,
    UNIQUE(menu_id, dish_id)
);

CREATE INDEX IF NOT EXISTS idx_menu_item_menu ON menu_item(menu_id);
CREATE INDEX IF NOT EXISTS idx_menu_item_dish ON menu_item(dish_id);


-- 4. meal_record — 摄入记录（HITL 确认后写入）
CREATE TABLE IF NOT EXISTS meal_record (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,                     -- 日期，如 "2026-08-03"
    meal_time       TEXT    NOT NULL,                     -- 餐次：breakfast / lunch / dinner
    dish_id         INTEGER NOT NULL REFERENCES dish(id) ON DELETE CASCADE,
    portion         REAL    NOT NULL DEFAULT 1.0,         -- 份量系数，1.0 = 1份
    grams           REAL    DEFAULT NULL,                 -- v1.2 实际摄入克重（NULL 时用 portion 换算）
    confirmed       INTEGER NOT NULL DEFAULT 0,           -- HITL 状态：0=待确认, 1=已确认, -1=已拒绝
    user_id         INTEGER REFERENCES app_user(id) ON DELETE SET NULL,  -- v1.1 记录归属用户（NULL=匿名/历史）
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_meal_record_date      ON meal_record(date);
CREATE INDEX IF NOT EXISTS idx_meal_record_confirmed ON meal_record(confirmed);
CREATE INDEX IF NOT EXISTS idx_meal_record_dish      ON meal_record(dish_id);
CREATE INDEX IF NOT EXISTS idx_meal_record_user      ON meal_record(user_id);


-- 5. user_profile — 用户画像（长期记忆）
CREATE TABLE IF NOT EXISTS user_profile (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    budget                  REAL    DEFAULT 0,            -- 预算（元/餐）
    flavor_preferences      TEXT    DEFAULT '',           -- 口味偏好，逗号分隔
    dietary_restrictions    TEXT    DEFAULT '',           -- 忌口/过敏，逗号分隔
    health_goals            TEXT    DEFAULT '',           -- 营养目标：高蛋白/控油/控糖/增肌/减脂
    -- 历史营养汇总（JSON），如 {"avg_calories": 650, "avg_protein": 28, ...}
    nutrition_summary       TEXT    DEFAULT '{}',
    user_id                 INTEGER REFERENCES app_user(id) ON DELETE CASCADE,  -- v1.1 画像归属用户（NULL=匿名/历史）
    created_at              TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at              TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_user_profile_user ON user_profile(user_id);


-- ============================================================
-- 常用查询视图
-- ============================================================

-- 按天/餐次查看完整菜单（含菜品信息）
CREATE VIEW IF NOT EXISTS v_menu_detail AS
SELECT
    m.date,
    m.meal_time,
    d.id          AS dish_id,
    d.name        AS dish_name,
    d.calories,
    d.protein,
    d.carbs,
    d.fat,
    d.price,
    d.category,
    d.flavor_tags
FROM menu m
JOIN menu_item mi ON m.id = mi.menu_id
JOIN dish d       ON mi.dish_id = d.id
ORDER BY m.date, m.meal_time, d.id;


-- 按天/餐次汇总营养摄入（仅已确认记录）
CREATE VIEW IF NOT EXISTS v_daily_nutrition AS
SELECT
    mr.date,
    mr.meal_time,
    SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
    SUM(d.protein  * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
    SUM(d.carbs    * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
    SUM(d.fat      * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat,
    COUNT(DISTINCT mr.id)         AS dish_count
FROM meal_record mr
JOIN dish d ON mr.dish_id = d.id
WHERE mr.confirmed = 1
GROUP BY mr.date, mr.meal_time
ORDER BY mr.date, mr.meal_time;


-- 按天汇总营养摄入（全天合计，仅已确认记录）
CREATE VIEW IF NOT EXISTS v_day_total AS
SELECT
    mr.date,
    SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
    SUM(d.protein  * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
    SUM(d.carbs    * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
    SUM(d.fat      * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat,
    COUNT(DISTINCT mr.id)         AS dish_count
FROM meal_record mr
JOIN dish d ON mr.dish_id = d.id
WHERE mr.confirmed = 1
GROUP BY mr.date
ORDER BY mr.date;


-- 按周汇总营养摄入（仅已确认记录）
CREATE VIEW IF NOT EXISTS v_weekly_nutrition AS
SELECT
    strftime('%Y-%W', mr.date)   AS week_key,
    mr.date,
    SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
    SUM(d.protein  * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
    SUM(d.carbs    * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
    SUM(d.fat      * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat
FROM meal_record mr
JOIN dish d ON mr.dish_id = d.id
WHERE mr.confirmed = 1
GROUP BY mr.date
ORDER BY mr.date;


-- 按周汇总（周合计 + 日均，仅已确认记录）
CREATE VIEW IF NOT EXISTS v_week_summary AS
SELECT
    strftime('%Y-%W', mr.date)   AS week_key,
    MIN(mr.date)                 AS start_date,
    MAX(mr.date)                 AS end_date,
    SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
    SUM(d.protein  * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
    SUM(d.carbs    * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
    SUM(d.fat      * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat,
    COUNT(DISTINCT mr.date)       AS day_count,
    COUNT(DISTINCT mr.id)         AS dish_count
FROM meal_record mr
JOIN dish d ON mr.dish_id = d.id
WHERE mr.confirmed = 1
GROUP BY week_key
ORDER BY week_key;


-- 6. chat_session — 对话会话（v1.3 新增）
CREATE TABLE IF NOT EXISTS chat_session (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL UNIQUE,                  -- 会话 UUID
    title       TEXT    DEFAULT '',                       -- 会话标题（首条用户消息截断）
    user_id     INTEGER REFERENCES app_user(id) ON DELETE SET NULL,  -- 归属用户（NULL=游客）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_chat_session_user ON chat_session(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_session_sid ON chat_session(session_id);


-- 7. chat_message — 对话消息（v1.3 新增）
CREATE TABLE IF NOT EXISTS chat_message (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL REFERENCES chat_session(session_id) ON DELETE CASCADE,
    role        TEXT    NOT NULL CHECK (role IN ('user','assistant')),  -- 消息角色
    content     TEXT    NOT NULL,                                      -- 消息文本
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_message(session_id);