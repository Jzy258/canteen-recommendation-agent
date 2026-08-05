import sqlite3
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional


# 默认 DB_PATH 基于 backend/ 包根目录解析（与运行目录无关，避免 backend/backend 嵌套）
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_db_env = os.getenv("DB_PATH")
if _db_env:
    if os.path.isabs(_db_env):
        DB_PATH = _db_env
    elif _db_env.startswith("backend/"):
        # 项目根相对（如 backend/data/canteen.db）→ 基于仓库根
        DB_PATH = os.path.join(os.path.dirname(_BACKEND_ROOT), _db_env)
    else:
        # 相对 backend 根（如 data/canteen.db）
        DB_PATH = os.path.join(_BACKEND_ROOT, _db_env)
else:
    DB_PATH = os.path.join(_BACKEND_ROOT, "data", "canteen.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


# =============================================================================
# 抽象接口 — 预留可换 MySQL
# =============================================================================

class DatabaseInterface(ABC):
    @abstractmethod
    def init_db(self):
        ...

    @abstractmethod
    def search_dishes(self, keyword: str = "", category: str = "",
                      max_price: float = 0) -> list[dict]:
        ...

    @abstractmethod
    def get_dish_by_id(self, dish_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def get_dish_by_name(self, name: str) -> Optional[dict]:
        ...

    @abstractmethod
    def get_all_dishes(self) -> list[dict]:
        ...

    @abstractmethod
    def bulk_insert_dishes(self, dishes: list[dict]) -> int:
        ...

    @abstractmethod
    def get_menu_by_date(self, date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_menu_by_date_range(self, start_date: str, end_date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_weekly_menu(self) -> list[dict]:
        ...

    @abstractmethod
    def get_dishes_for_menu(self, date: str, meal_time: str) -> list[dict]:
        ...

    @abstractmethod
    def add_meal_record(self, date: str, meal_time: str, dish_id: int,
                        portion: float = 1.0,
                        user_id: Optional[int] = None,
                        grams: Optional[float] = None) -> int:
        ...

    @abstractmethod
    def confirm_meal_record(self, record_id: int) -> bool:
        ...

    @abstractmethod
    def reject_meal_record(self, record_id: int) -> bool:
        ...

    @abstractmethod
    def update_meal_record(self, record_id: int, date: str | None = None,
                           meal_time: str | None = None,
                           dish_id: int | None = None,
                           portion: float | None = None,
                           grams: float | None = None,
                           user_id: int | None = None) -> bool:
        ...

    @abstractmethod
    def delete_meal_record(self, record_id: int,
                           user_id: int | None = None) -> bool:
        ...

    @abstractmethod
    def get_meal_record(self, record_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def get_pending_records(self) -> list[dict]:
        ...

    @abstractmethod
    def get_pending_records_by_date(self, date: str,
                                    meal_time: str = "") -> list[dict]:
        ...

    @abstractmethod
    def get_pending_record(self, record_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def confirm_records(self, record_ids: list[int]) -> int:
        ...

    @abstractmethod
    def reject_records(self, record_ids: list[int]) -> int:
        ...

    @abstractmethod
    def get_records_by_date(self, date: str,
                            user_id: Optional[int] = None) -> list[dict]:
        ...

    @abstractmethod
    def get_records_in_range(self, start_date: str, end_date: str,
                             meal_time: str = "",
                             user_id: Optional[int] = None) -> list[dict]:
        ...

    @abstractmethod
    def get_daily_nutrition(self, date: str,
                            user_id: Optional[int] = None) -> list[dict]:
        ...

    @abstractmethod
    def get_day_total(self, date: str,
                      user_id: Optional[int] = None) -> Optional[dict]:
        ...

    @abstractmethod
    def get_weekly_nutrition(self, start_date: str, end_date: str,
                             user_id: Optional[int] = None) -> list[dict]:
        ...

    @abstractmethod
    def get_weekly_summary(self, start_date: str, end_date: str,
                           user_id: Optional[int] = None) -> Optional[dict]:
        ...

    @abstractmethod
    def get_weekly_trend(self, end_date: str = "", days: int = 7,
                         user_id: Optional[int] = None) -> list[dict]:
        ...

    @abstractmethod
    def get_user_profile(self, user_id: Optional[int] = None) -> Optional[dict]:
        ...

    @abstractmethod
    def upsert_user_profile(self, budget: float = 0,
                            budget_min: float = 0,
                            flavor_preferences: str = "",
                            dietary_restrictions: str = "",
                            health_goals: str = "",
                            user_id: Optional[int] = None) -> int:
        ...

    @abstractmethod
    def update_nutrition_summary(self, summary_json: str,
                                 user_id: Optional[int] = None) -> bool:
        ...

    @abstractmethod
    def get_dishes_by_weather_tag(self, weather_type: str) -> list[dict]:
        ...

    # ---- v1.1 用户系统 ----

    @abstractmethod
    def create_user(self, username: str, password_hash: str,
                    role: str = "user", display_name: str = "") -> int:
        ...

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[dict]:
        ...

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def update_user_login(self, user_id: int) -> bool:
        ...

    @abstractmethod
    def change_user_password(self, user_id: int, password_hash: str) -> bool:
        ...

    @abstractmethod
    def set_user_status(self, user_id: int, status: int) -> bool:
        ...

    # ---- v1.3 chat（历史对话） ----

    @abstractmethod
    def _ensure_chat_session(self, session_id: str,
                             user_id: Optional[int] = None,
                             title: str = "") -> int:
        ...

    @abstractmethod
    def add_chat_message(self, session_id: str, role: str, content: str,
                         user_id: Optional[int] = None) -> int:
        ...

    @abstractmethod
    def get_chat_messages(self, session_id: str) -> list[dict]:
        ...

    @abstractmethod
    def list_chat_sessions(self, user_id: Optional[int] = None,
                           limit: int = 50) -> list[dict]:
        ...

    @abstractmethod
    def delete_chat_session(self, session_id: str,
                            user_id: Optional[int] = None) -> bool:
        ...


# =============================================================================
# SQLite 实现
# =============================================================================

class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self):
        """自动初始化：确保库结构完整且幂等。
        - 老库（无 dish 表）→ 执行完整 schema
        - 部分表已存在的旧库 → 先做增量迁移（v1.1 列 + v1.2 列/视图），再补建缺失对象
        - 新库 → 直接执行 schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                has_dish = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='dish'"
                ).fetchone()
                has_meal = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='meal_record'"
                ).fetchone()
                if has_dish is None:
                    # 老库部分表存在时先迁移列（同连接内提交，新连接才能看到新列）
                    if has_meal is not None:
                        self._migrate_v11(conn)
                        self._migrate_v12(conn)
                        self._migrate_v13(conn)
                        self._migrate_v14(conn)
                    self.init_db()
                    return
                self._migrate_v11(conn)
                self._migrate_v12(conn)
                self._migrate_v13(conn)
                self._migrate_v14(conn)
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    def _migrate_v11(self, conn):
        """v1.0 → v1.1 增量迁移：
        - 确保 app_user 表存在（旧库无此表时创建）
        - meal_record/user_profile 增加 user_id 列
        幂等：先检查对象是否已存在，缺失才创建。"""
        try:
            # 1) app_user 表
            tbl = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='app_user'"
            ).fetchone()
            if tbl is None:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS app_user (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        username      TEXT    NOT NULL UNIQUE,
                        password_hash TEXT    NOT NULL,
                        role          TEXT    NOT NULL DEFAULT 'user'
                                        CHECK (role IN ('admin','user')),
                        display_name  TEXT    DEFAULT '',
                        status        INTEGER NOT NULL DEFAULT 1,
                        created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                        last_login_at TEXT
                    )""")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_app_user_username ON app_user(username)")
            # 2) user_id 列（SQLite 限制：ADD COLUMN 不能带 REFERENCES，故仅加列）
            for table, column in (("meal_record", "user_id"),
                                  ("user_profile", "user_id")):
                cols = {r["name"] for r in conn.execute(
                    f"PRAGMA table_info({table})").fetchall()}
                if column not in cols:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} INTEGER")
            # 立即提交迁移，避免后续 init_db() 的新连接看不到新列
            conn.commit()
        except sqlite3.Error:
            pass

    def _migrate_v12(self, conn):
        """v1.1 → v1.2 增量迁移（克重调控）：
        - dish 增加 serving_grams 列（标准份量克数）
        - meal_record 增加 grams 列（实际摄入克重）
        - 重建聚合视图（旧视图定义的 portion 系数需升级为克重换算）
        幂等：检查列/视图存在性。"""
        try:
            # 1) 列
            for table, column in (("dish", "serving_grams"),
                                  ("meal_record", "grams")):
                cols = {r["name"] for r in conn.execute(
                    f"PRAGMA table_info({table})").fetchall()}
                if column not in cols:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} REAL")
            # user_profile 增加预算下限列（v1.3 预算范围；budget 作为上限）
            up_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_profile'"
            ).fetchone()
            if up_exists is not None:
                up_cols = {r["name"] for r in conn.execute(
                    "PRAGMA table_info(user_profile)").fetchall()}
                if "budget_min" not in up_cols:
                    conn.execute("ALTER TABLE user_profile ADD COLUMN budget_min REAL")
            # 2) 重建聚合视图（schema.sql 已定义克重换算版，仅重建涉及克重的 4 个）
            views_to_rebuild = ("v_daily_nutrition", "v_day_total",
                                "v_weekly_nutrition", "v_week_summary")
            for view in views_to_rebuild:
                conn.execute(f"DROP VIEW IF EXISTS {view}")
            schema = open(SCHEMA_PATH, "r", encoding="utf-8").read()
            for stmt in schema.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                upper = stmt.upper()
                if "CREATE VIEW" in upper:
                    create_line = next(
                        (ln for ln in stmt.splitlines() if "CREATE VIEW" in ln.upper()),
                        "")
                    if any(v in create_line for v in views_to_rebuild):
                        conn.executescript(stmt + ";")
        except sqlite3.Error:
            pass

    def _migrate_v13(self, conn):
        """v1.2 → v1.3 增量迁移（历史对话）：
        - 创建 chat_session / chat_message 表
        幂等：先检查表是否已存在。"""
        try:
            for tbl in ("chat_session", "chat_message"):
                exists = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (tbl,)).fetchone()
                if exists is None:
                    schema = open(SCHEMA_PATH, "r", encoding="utf-8").read()
                    for stmt in schema.split(";"):
                        stmt = stmt.strip()
                        if not stmt:
                            continue
                        upper = stmt.upper()
                        if f"CREATE TABLE IF NOT EXISTS {tbl.upper()}" in upper:
                            conn.executescript(stmt + ";")
            conn.commit()
        except sqlite3.Error:
            pass

    def _migrate_v14(self, conn):
        """v1.3 → v1.4 增量迁移：food_record 增加 fat / carbs 列（饮食记录记录脂肪/碳水）。"""
        try:
            for column in ("fat", "carbs", "grams", "recommended_grams"):
                cols = {r["name"] for r in conn.execute(
                    "PRAGMA table_info(food_record)").fetchall()}
                if column not in cols:
                    conn.execute(
                        f"ALTER TABLE food_record ADD COLUMN {column} REAL NOT NULL DEFAULT 0")
            # 回填历史聊天记录：按菜名取 dish 的推荐克重（serving_grams）
            conn.execute(
                """UPDATE food_record
                   SET recommended_grams = COALESCE(
                       (SELECT serving_grams FROM dish WHERE dish.name = food_record.name), 0)
                   WHERE remark = '（聊天记录）'
                     AND (recommended_grams IS NULL OR recommended_grams = 0)""")
            conn.commit()
        except sqlite3.Error:
            pass

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = f.read()
        with self._connect() as conn:
            conn.executescript(schema)

    # ---- dish ----

    def search_dishes(self, keyword: str = "", category: str = "",
                      max_price: float = 0) -> list[dict]:
        sql = "SELECT * FROM dish WHERE 1=1"
        params = []
        if keyword:
            sql += " AND name LIKE ?"
            params.append(f"%{keyword}%")
        if category:
            sql += " AND category = ?"
            params.append(category)
        if max_price > 0:
            sql += " AND price <= ?"
            params.append(max_price)
        sql += " ORDER BY id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_dish_by_id(self, dish_id: int) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM dish WHERE id = ?",
                               (dish_id,)).fetchone()
        return dict(row) if row else None

    def get_dish_by_name(self, name: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM dish WHERE name = ?",
                               (name,)).fetchone()
        return dict(row) if row else None

    def get_all_dishes(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM dish ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def bulk_insert_dishes(self, dishes: list[dict]) -> int:
        sql = """INSERT OR IGNORE INTO dish
                 (name, calories, protein, carbs, fat, price, category,
                  flavor_tags, serving_grams, source)
                 VALUES (:name, :calories, :protein, :carbs, :fat, :price,
                         :category, :flavor_tags, :serving_grams, :source)"""
        with self._connect() as conn:
            # 兼容旧数据（无 serving_grams 键时补默认 150g）
            rows = [dict(r, serving_grams=r.get("serving_grams") or 150)
                    for r in dishes]
            conn.executemany(sql, rows)
            return conn.total_changes

    # ---- admin: dish CRUD ----

    def add_dish(self, dish: dict) -> int:
        """新增菜品。返回 id；重名抛 sqlite3.IntegrityError。"""
        sql = """INSERT INTO dish
                 (name, calories, protein, carbs, fat, price, category, flavor_tags, source)
                 VALUES (:name, :calories, :protein, :carbs, :fat, :price, :category, :flavor_tags, :source)"""
        with self._connect() as conn:
            cur = conn.execute(sql, {
                "name": dish["name"],
                "calories": dish.get("calories", 0),
                "protein": dish.get("protein", 0),
                "carbs": dish.get("carbs", 0),
                "fat": dish.get("fat", 0),
                "price": dish.get("price", 0),
                "category": dish.get("category", ""),
                "flavor_tags": dish.get("flavor_tags", ""),
                "source": dish.get("source", ""),
            })
            return cur.lastrowid

    def update_dish(self, dish_id: int, dish: dict) -> bool:
        """更新菜品（仅更新传入的非空字段；name 冲突抛 IntegrityError）。"""
        fields = {k: dish[k] for k in (
            "name", "calories", "protein", "carbs", "fat", "price",
            "category", "flavor_tags", "source") if k in dish and dish[k] not in (None, "")}
        if not fields:
            return False
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self._connect() as conn:
            cur = conn.execute(f"UPDATE dish SET {sets} WHERE id = ?",
                               (*fields.values(), dish_id))
            return cur.rowcount > 0

    def delete_dish(self, dish_id: int) -> bool:
        """删除菜品（menu_item 级联删除；若有摄入记录则保留 dish 但标记禁用由上层处理）。"""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM dish WHERE id = ?", (dish_id,))
            return cur.rowcount > 0

    # ---- admin: menu CRUD ----

    def add_menu_item(self, date: str, meal_time: str, dish_ids: list[int]) -> dict:
        """为指定日期餐次设置菜单菜品（覆盖式：先删后插）。返回 {menu_id, added}。"""
        with self._connect() as conn:
            # upsert menu 行
            row = conn.execute(
                "SELECT id FROM menu WHERE date = ? AND meal_time = ?",
                (date, meal_time)).fetchone()
            if row:
                menu_id = row["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO menu (date, meal_time) VALUES (?, ?)",
                    (date, meal_time))
                menu_id = cur.lastrowid
            # 覆盖式重设
            conn.execute("DELETE FROM menu_item WHERE menu_id = ?", (menu_id,))
            added = 0
            for did in dish_ids:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO menu_item (menu_id, dish_id) VALUES (?, ?)",
                        (menu_id, did))
                    added += 1
                except sqlite3.Error:
                    continue
            return {"menu_id": menu_id, "added": added}

    def delete_menu(self, date: str, meal_time: str) -> bool:
        """删除指定日期餐次的菜单（menu_item 级联删除）。"""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM menu WHERE date = ? AND meal_time = ?",
                (date, meal_time))
            return cur.rowcount > 0

    # ---- admin: 全局统计 ----

    def get_global_stats(self) -> dict:
        """全局运营统计：用户数 / 菜品数 / 菜单数 / 摄入记录数 / 今日记录数。"""
        with self._connect() as conn:
            users = conn.execute("SELECT COUNT(*) c FROM app_user").fetchone()["c"]
            dishes = conn.execute("SELECT COUNT(*) c FROM dish").fetchone()["c"]
            menus = conn.execute("SELECT COUNT(*) c FROM menu").fetchone()["c"]
            records = conn.execute("SELECT COUNT(*) c FROM meal_record").fetchone()["c"]
            today = conn.execute(
                "SELECT COUNT(*) c FROM meal_record WHERE date = date('now','localtime')"
            ).fetchone()["c"]
        return {
            "user_count": users,
            "dish_count": dishes,
            "menu_count": menus,
            "record_count": records,
            "today_record_count": today,
        }


    # ---- menu / menu_item ----

    def get_menu_by_date(self, date: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM v_menu_detail WHERE date = ? ORDER BY meal_time, dish_id",
                (date,)).fetchall()
        return [dict(r) for r in rows]

    def get_menu_by_date_range(self, start_date: str, end_date: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM v_menu_detail WHERE date BETWEEN ? AND ? ORDER BY date, meal_time, dish_id",
                (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]

    def get_weekly_menu(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM v_menu_detail ORDER BY date, meal_time, dish_id").fetchall()
        return [dict(r) for r in rows]

    def get_dishes_for_menu(self, date: str, meal_time: str) -> list[dict]:
        sql = """SELECT d.* FROM dish d
                 JOIN menu_item mi ON d.id = mi.dish_id
                 JOIN menu m ON mi.menu_id = m.id
                 WHERE m.date = ? AND m.meal_time = ?
                 ORDER BY d.id"""
        with self._connect() as conn:
            rows = conn.execute(sql, (date, meal_time)).fetchall()
        return [dict(r) for r in rows]

    # ---- meal_record ----

    @staticmethod
    def _serving_factor_sql():
        """克重换算系数 SQL 片段：grams 有值且 serving_grams>0 时按克重折算，
        否则回退份数 portion。"""
        return ("(CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0 "
                "THEN mr.grams / d.serving_grams ELSE mr.portion END)")

    def add_meal_record(self, date: str, meal_time: str, dish_id: int,
                        portion: float = 1.0,
                        user_id: Optional[int] = None,
                        grams: Optional[float] = None) -> int:
        sql = """INSERT INTO meal_record (date, meal_time, dish_id, portion, user_id, grams)
                 VALUES (?, ?, ?, ?, ?, ?)"""
        with self._connect() as conn:
            cur = conn.execute(sql, (date, meal_time, dish_id, portion, user_id, grams))
            return cur.lastrowid

    def confirm_meal_record(self, record_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE meal_record SET confirmed = 1 WHERE id = ? AND confirmed = 0",
                (record_id,))
            ok = cur.rowcount > 0
            uid = None
            if ok:
                row = conn.execute(
                    "SELECT user_id FROM meal_record WHERE id = ?",
                    (record_id,)).fetchone()
                if row:
                    uid = row["user_id"]
        if ok:
            self._refresh_profile_summary(user_id=uid)
        return ok

    def reject_meal_record(self, record_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE meal_record SET confirmed = -1 WHERE id = ? AND confirmed = 0",
                (record_id,))
            return cur.rowcount > 0

    def update_meal_record(self, record_id: int, date: str | None = None,
                           meal_time: str | None = None,
                           dish_id: int | None = None,
                           portion: float | None = None,
                           grams: float | None = None,
                           user_id: int | None = None) -> bool:
        """修改一条饮食记录。仅更新传入的非空字段。
        user_id 用于越权校验：记录归属用户不匹配则拒绝（None 时跳过校验）。
        修改已确认记录后刷新营养汇总。"""
        with self._connect() as conn:
            # 越权校验
            row = conn.execute(
                "SELECT * FROM meal_record WHERE id = ?", (record_id,)).fetchone()
            if row is None:
                return False
            if user_id is not None and row["user_id"] != user_id:
                return False
            sets, params = [], []
            if date is not None:
                sets.append("date = ?"); params.append(date)
            if meal_time is not None:
                sets.append("meal_time = ?"); params.append(meal_time)
            if dish_id is not None:
                sets.append("dish_id = ?"); params.append(dish_id)
            if portion is not None:
                sets.append("portion = ?"); params.append(portion)
            if grams is not None:
                sets.append("grams = ?"); params.append(grams)
            if not sets:
                return True
            params.append(record_id)
            cur = conn.execute(
                f"UPDATE meal_record SET {', '.join(sets)} WHERE id = ?",
                params)
            ok = cur.rowcount > 0
            owner = row["user_id"]
        if ok and row["confirmed"] == 1:
            self._refresh_profile_summary(user_id=owner)
        return ok

    def delete_meal_record(self, record_id: int,
                           user_id: int | None = None) -> bool:
        """物理删除一条饮食记录。user_id 用于越权校验（None 时跳过）。"""
        with self._connect() as conn:
            if user_id is None:
                cur = conn.execute(
                    "DELETE FROM meal_record WHERE id = ?", (record_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM meal_record WHERE id = ? AND user_id = ?",
                    (record_id, user_id))
            return cur.rowcount > 0

    # ---- food_record：手工饮食记录（CRUD）----

    def get_food_records(self, start_date: str = "", end_date: str = "",
                         meal_time: str = "", user_id: int | None = None) -> list[dict]:
        """返回 [start_date, end_date] 内手工饮食记录，可按餐次过滤。"""
        sql = "SELECT * FROM food_record WHERE 1=1"
        params: list = []
        if user_id is not None:
            sql += " AND user_id = ?"; params.append(user_id)
        if start_date:
            sql += " AND date >= ?"; params.append(start_date)
        if end_date:
            sql += " AND date <= ?"; params.append(end_date)
        if meal_time:
            # 兼容中英文餐次（agent 聊天记录可能写入中文，如“早餐/其他”）
            variants = {
                "breakfast": ("breakfast", "早餐"),
                "lunch": ("lunch", "午餐"),
                "dinner": ("dinner", "晚餐"),
                "other": ("other", "其他"),
            }.get(meal_time, (meal_time,))
            placeholders = ",".join("?" for _ in variants)
            sql += f" AND meal_time IN ({placeholders})"
            params.extend(variants)
        sql += " ORDER BY date DESC, meal_time, id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def add_food_record(self, date: str, meal_time: str, name: str,
                        price: float = 0, calories: float = 0, protein: float = 0,
                        fat: float = 0, carbs: float = 0, grams: float = 0,
                        recommended_grams: float = 0,
                        remark: str = "", user_id: int | None = None) -> int:
        sql = """INSERT INTO food_record (date, meal_time, name, price, calories, protein, fat, carbs, grams, recommended_grams, remark, user_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        with self._connect() as conn:
            cur = conn.execute(
                sql, (date, meal_time, name, price, calories, protein, fat, carbs, grams, recommended_grams, remark, user_id))
            return cur.lastrowid

    def update_food_record(self, record_id: int, date: str | None = None,
                           meal_time: str | None = None, name: str | None = None,
                           price: float | None = None, calories: float | None = None,
                           protein: float | None = None, fat: float | None = None,
                           carbs: float | None = None, grams: float | None = None,
                           recommended_grams: float | None = None,
                           remark: str | None = None,
                           user_id: int | None = None) -> bool:
        """修改一条手工饮食记录。仅更新传入字段；user_id 用于越权校验。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM food_record WHERE id = ?", (record_id,)).fetchone()
            if row is None:
                return False
            if user_id is not None and row["user_id"] != user_id:
                return False
            sets, params = [], []
            if date is not None: sets.append("date = ?"); params.append(date)
            if meal_time is not None: sets.append("meal_time = ?"); params.append(meal_time)
            if name is not None: sets.append("name = ?"); params.append(name)
            if price is not None: sets.append("price = ?"); params.append(price)
            if calories is not None: sets.append("calories = ?"); params.append(calories)
            if protein is not None: sets.append("protein = ?"); params.append(protein)
            if fat is not None: sets.append("fat = ?"); params.append(fat)
            if carbs is not None: sets.append("carbs = ?"); params.append(carbs)
            if grams is not None: sets.append("grams = ?"); params.append(grams)
            if recommended_grams is not None: sets.append("recommended_grams = ?"); params.append(recommended_grams)
            if remark is not None: sets.append("remark = ?"); params.append(remark)
            if not sets:
                return True
            sets.append("updated_at = datetime('now','localtime')")
            params.append(record_id)
            cur = conn.execute(
                f"UPDATE food_record SET {', '.join(sets)} WHERE id = ?", params)
            return cur.rowcount > 0

    def delete_food_record(self, record_id: int, user_id: int | None = None) -> bool:
        """物理删除一条手工饮食记录。"""
        with self._connect() as conn:
            if user_id is None:
                cur = conn.execute(
                    "DELETE FROM food_record WHERE id = ?", (record_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM food_record WHERE id = ? AND user_id = ?",
                    (record_id, user_id))
            return cur.rowcount > 0

    def get_meal_record(self, record_id: int) -> Optional[dict]:
        """按 id 查询单条饮食记录（含菜品信息），不存在返回 None。"""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT mr.*, d.name AS dish_name, d.category, d.price
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.id = ?""",
                (record_id,)).fetchone()
        return dict(row) if row else None

    def confirm_records(self, record_ids: list[int]) -> int:
        """批量确认，返回实际确认条数。"""
        if not record_ids:
            return 0
        placeholders = ",".join("?" * len(record_ids))
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE meal_record SET confirmed = 1 "
                f"WHERE id IN ({placeholders}) AND confirmed = 0",
                record_ids)
            n = cur.rowcount
            uids = {r["user_id"] for r in conn.execute(
                f"SELECT DISTINCT user_id FROM meal_record WHERE id IN ({placeholders})",
                record_ids).fetchall()}
        if n > 0:
            for uid in uids:
                self._refresh_profile_summary(user_id=uid)
        return n

    def reject_records(self, record_ids: list[int]) -> int:
        """批量拒绝，返回实际拒绝条数。"""
        if not record_ids:
            return 0
        placeholders = ",".join("?" * len(record_ids))
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE meal_record SET confirmed = -1 "
                f"WHERE id IN ({placeholders}) AND confirmed = 0",
                record_ids)
            return cur.rowcount

    def get_pending_records(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT mr.*, d.name AS dish_name, d.calories, d.protein, d.carbs, d.fat
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 0
                   ORDER BY mr.date, mr.meal_time""").fetchall()
        return [dict(r) for r in rows]

    def get_pending_records_by_date(self, date: str,
                                    meal_time: str = "") -> list[dict]:
        sql = """SELECT mr.*, d.name AS dish_name, d.calories, d.protein, d.carbs, d.fat
                 FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                 WHERE mr.confirmed = 0 AND mr.date = ?"""
        params: list = [date]
        if meal_time:
            sql += " AND mr.meal_time = ?"
            params.append(meal_time)
        sql += " ORDER BY mr.meal_time, mr.id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_pending_record(self, record_id: int) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT mr.*, d.name AS dish_name, d.calories, d.protein, d.carbs, d.fat
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.id = ? AND mr.confirmed = 0""",
                (record_id,)).fetchone()
        return dict(row) if row else None

    def _refresh_profile_summary(self, user_id: Optional[int] = None):
        """确认记录后，重算该用户已确认记录的营养汇总并写入 user_profile。
        汇总内容：总摄入、日均营养、按餐次平均、菜品多样性、近7天趋势。
        与 B 的 store.summarize_nutrition 协调：仅更新本模块的统计键，
        保留既有 summary 中的其他键（如 B 写入的 days/week_key），避免互相覆盖。"""
        with self._connect() as conn:
            f = self._serving_factor_sql()
            sql = f"""SELECT
                       COUNT(*) AS record_count,
                       COUNT(DISTINCT date) AS day_count,
                       COUNT(DISTINCT d.id) AS dish_kind_count,
                       ROUND(SUM(d.calories * {f}), 1) AS total_calories,
                       ROUND(SUM(d.protein * {f}), 1) AS total_protein,
                       ROUND(SUM(d.carbs * {f}), 1) AS total_carbs,
                       ROUND(SUM(d.fat * {f}), 1) AS total_fat
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 1"""
            params: list = []
            if user_id is not None:
                sql += " AND mr.user_id = ?"
                params.append(user_id)
            row = conn.execute(sql, params).fetchone()

        import json
        # 读取既有 summary，保留 A 不管理的键（协调 B 的 summarize_nutrition）
        existing = {}
        prof = self.get_user_profile(user_id=user_id)
        if prof and prof.get("nutrition_summary"):
            try:
                existing = json.loads(prof["nutrition_summary"])
            except Exception:
                existing = {}
        merged = dict(existing)  # 保留 B 的键（days/week_key 等）

        if not row or row["record_count"] == 0:
            summary = {}
        else:
            days = row["day_count"] or 1
            summary = {
                "record_count": row["record_count"],
                "day_count": row["day_count"],
                "dish_kind_count": row["dish_kind_count"],
                "total_calories": row["total_calories"],
                "total_protein": row["total_protein"],
                "total_carbs": row["total_carbs"],
                "total_fat": row["total_fat"],
                "avg_calories": round(row["total_calories"] / days, 1),
                "avg_protein": round(row["total_protein"] / days, 1),
                "avg_carbs": round(row["total_carbs"] / days, 1),
                "avg_fat": round(row["total_fat"] / days, 1),
            }
            summary["meal_averages"] = self._meal_averages(user_id)
            summary["recent_trend"] = self._recent_trend(user_id=user_id)
        merged.update(summary)  # A 的键覆盖，B 的键保留

        if self.get_user_profile(user_id=user_id) is None:
            self.upsert_user_profile(user_id=user_id)
        self.update_nutrition_summary(json.dumps(merged, ensure_ascii=False),
                                      user_id=user_id)

    def _meal_averages(self, user_id: Optional[int] = None) -> dict:
        """按餐次统计平均摄入。"""
        f = self._serving_factor_sql()
        with self._connect() as conn:
            sql = f"""SELECT mr.meal_time,
                          ROUND(SUM(d.calories * {f}) / COUNT(DISTINCT mr.date), 1) AS avg_calories
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 1"""
            params: list = []
            if user_id is not None:
                sql += " AND mr.user_id = ?"
                params.append(user_id)
            sql += " GROUP BY mr.meal_time"
            rows = conn.execute(sql, params).fetchall()
        return {r["meal_time"]: r["avg_calories"] for r in rows}

    def _recent_trend(self, days: int = 7,
                      user_id: Optional[int] = None) -> list[dict]:
        """最近 N 天每日热量摄入（仅含实际有记录的天）。"""
        f = self._serving_factor_sql()
        with self._connect() as conn:
            sql = f"""SELECT mr.date,
                          ROUND(SUM(d.calories * {f}), 1) AS calories
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 1"""
            params: list = []
            if user_id is not None:
                sql += " AND mr.user_id = ?"
                params.append(user_id)
            sql += " GROUP BY mr.date ORDER BY mr.date DESC LIMIT ?"
            params.append(days)
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_records_by_date(self, date: str,
                            user_id: Optional[int] = None) -> list[dict]:
        f = self._serving_factor_sql()
        sql = f"""SELECT mr.*, d.name AS dish_name, d.calories, d.protein, d.carbs, d.fat,
                         d.serving_grams,
                         ROUND(d.calories * {f}, 1) AS intake_calories,
                         ROUND(d.protein * {f}, 1) AS intake_protein,
                         ROUND(d.carbs * {f}, 1) AS intake_carbs,
                         ROUND(d.fat * {f}, 1) AS intake_fat
                  FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                  WHERE mr.date = ? AND mr.confirmed = 1"""
        params: list = [date]
        if user_id is not None:
            sql += " AND mr.user_id = ?"
            params.append(user_id)
        sql += " ORDER BY mr.meal_time"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_records_in_range(self, start_date: str, end_date: str,
                             meal_time: str = "",
                             user_id: Optional[int] = None) -> list[dict]:
        """返回 [start_date, end_date] 内已确认的饮食记录，可按餐次过滤。
        含实际摄入营养（intake_*，按 grams/serving_grams 或 portion 折算）。"""
        f = self._serving_factor_sql()
        sql = (f"""SELECT mr.*, d.name AS dish_name, d.calories, d.protein,
                          d.carbs, d.fat, d.price, d.category,
                          d.serving_grams,
                          ROUND(d.calories * {f}, 1) AS intake_calories,
                          ROUND(d.protein * {f}, 1) AS intake_protein,
                          ROUND(d.carbs * {f}, 1) AS intake_carbs,
                          ROUND(d.fat * {f}, 1) AS intake_fat
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 1 AND mr.date BETWEEN ? AND ?""")
        params: list = [start_date, end_date]
        if meal_time:
            sql += " AND mr.meal_time = ?"
            params.append(meal_time)
        if user_id is not None:
            sql += " AND mr.user_id = ?"
            params.append(user_id)
        sql += " ORDER BY mr.date DESC, mr.meal_time, mr.id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_daily_nutrition(self, date: str,
                            user_id: Optional[int] = None) -> list[dict]:
        with self._connect() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM v_daily_nutrition WHERE date = ? ORDER BY meal_time",
                    (date,)).fetchall()
            else:
                rows = conn.execute(
                    """SELECT mr.meal_time,
                              SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                     THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
                              SUM(d.protein * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                    THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
                              SUM(d.carbs * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                  THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
                              SUM(d.fat * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat,
                              COUNT(DISTINCT mr.id) AS dish_count
                       FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                       WHERE mr.confirmed = 1 AND mr.date = ? AND mr.user_id = ?
                       GROUP BY mr.meal_time ORDER BY mr.meal_time""",
                    (date, user_id)).fetchall()
        return [dict(r) for r in rows]

    def get_day_total(self, date: str,
                      user_id: Optional[int] = None) -> Optional[dict]:
        with self._connect() as conn:
            if user_id is None:
                row = conn.execute(
                    "SELECT * FROM v_day_total WHERE date = ?",
                    (date,)).fetchone()
            else:
                row = conn.execute(
                    """SELECT mr.date,
                              SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                     THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
                              SUM(d.protein * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                    THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
                              SUM(d.carbs * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                  THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
                              SUM(d.fat * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat,
                              COUNT(DISTINCT mr.id) AS dish_count
                       FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                       WHERE mr.confirmed = 1 AND mr.date = ? AND mr.user_id = ?
                       GROUP BY mr.date""",
                    (date, user_id)).fetchone()
        return dict(row) if row else None

    def get_weekly_nutrition(self, start_date: str, end_date: str,
                             user_id: Optional[int] = None) -> list[dict]:
        with self._connect() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM v_weekly_nutrition WHERE date BETWEEN ? AND ? ORDER BY date",
                    (start_date, end_date)).fetchall()
            else:
                rows = conn.execute(
                    """SELECT strftime('%Y-%W', mr.date) AS week_key, mr.date,
                              SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                     THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
                              SUM(d.protein * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                    THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
                              SUM(d.carbs * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                  THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
                              SUM(d.fat * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat
                       FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                       WHERE mr.confirmed = 1 AND mr.date BETWEEN ? AND ? AND mr.user_id = ?
                       GROUP BY mr.date ORDER BY mr.date""",
                    (start_date, end_date, user_id)).fetchall()
        return [dict(r) for r in rows]

    def get_weekly_summary(self, start_date: str, end_date: str,
                           user_id: Optional[int] = None) -> Optional[dict]:
        with self._connect() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM v_week_summary WHERE start_date >= ? AND end_date <= ?",
                    (start_date, end_date)).fetchall()
            else:
                rows = conn.execute(
                    """SELECT strftime('%Y-%W', mr.date) AS week_key,
                              MIN(mr.date) AS start_date,
                              MAX(mr.date) AS end_date,
                              SUM(d.calories * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                     THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_calories,
                              SUM(d.protein * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                    THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_protein,
                              SUM(d.carbs * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                  THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_carbs,
                              SUM(d.fat * (CASE WHEN mr.grams IS NOT NULL AND d.serving_grams > 0
                                                THEN mr.grams / d.serving_grams ELSE mr.portion END)) AS total_fat,
                              COUNT(DISTINCT mr.date) AS day_count,
                              COUNT(DISTINCT mr.id) AS dish_count
                       FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                       WHERE mr.confirmed = 1 AND mr.date BETWEEN ? AND ? AND mr.user_id = ?
                       GROUP BY week_key ORDER BY week_key""",
                    (start_date, end_date, user_id)).fetchall()
        result = [dict(r) for r in rows]
        if not result:
            return None
        agg = {
            "total_calories": sum(r["total_calories"] or 0 for r in result),
            "total_protein":  sum(r["total_protein"] or 0 for r in result),
            "total_carbs":    sum(r["total_carbs"] or 0 for r in result),
            "total_fat":      sum(r["total_fat"] or 0 for r in result),
            "day_count":      sum(r["day_count"] or 0 for r in result),
            "dish_count":     sum(r["dish_count"] or 0 for r in result),
            "week_key":       result[0]["week_key"],
            "start_date":     result[0]["start_date"],
            "end_date":       result[-1]["end_date"],
        }
        return agg

    def get_weekly_trend(self, end_date: str = "", days: int = 7,
                         user_id: Optional[int] = None) -> list[dict]:
        """返回 [end_date-days+1, end_date] 窗口内每天的营养合计。
        缺失日期补零，保证连续 days 天的序列，方便前端画趋势图。"""
        from datetime import date, datetime, timedelta

        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 7
        if days <= 0:
            days = 7

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except (TypeError, ValueError):
                end = date.today()
        else:
            end = date.today()
        start = end - timedelta(days=days - 1)

        with self._connect() as conn:
            # 数据源与饮食记录页一致（food_record）：按实际克重/推荐克重折算营养
            sql = """SELECT fr.date,
                              SUM(fr.calories * (CASE WHEN fr.grams > 0 AND fr.recommended_grams > 0
                                                     THEN fr.grams / fr.recommended_grams ELSE 1 END)) AS total_calories,
                              SUM(fr.protein * (CASE WHEN fr.grams > 0 AND fr.recommended_grams > 0
                                                     THEN fr.grams / fr.recommended_grams ELSE 1 END)) AS total_protein,
                              SUM(fr.carbs * (CASE WHEN fr.grams > 0 AND fr.recommended_grams > 0
                                                   THEN fr.grams / fr.recommended_grams ELSE 1 END)) AS total_carbs,
                              SUM(fr.fat * (CASE WHEN fr.grams > 0 AND fr.recommended_grams > 0
                                                 THEN fr.grams / fr.recommended_grams ELSE 1 END)) AS total_fat,
                              COUNT(DISTINCT fr.id) AS dish_count
                       FROM food_record fr
                       WHERE fr.date BETWEEN ? AND ?"""
            params: list = [start.isoformat(), end.isoformat()]
            if user_id is not None:
                sql += " AND fr.user_id = ?"
                params.append(user_id)
            sql += " GROUP BY fr.date ORDER BY fr.date"
            rows = conn.execute(sql, params).fetchall()

        day_map = {r["date"]: dict(r) for r in rows}
        trend = []
        for i in range(days):
            d = start + timedelta(days=i)
            dstr = d.isoformat()
            row = day_map.get(dstr)
            trend.append({
                "date": dstr,
                "total_calories": row["total_calories"] if row else 0,
                "total_protein":  row["total_protein"] if row else 0,
                "total_carbs":    row["total_carbs"] if row else 0,
                "total_fat":      row["total_fat"] if row else 0,
                "dish_count":     row["dish_count"] if row else 0,
            })
        return trend

    # ---- v1.1 app_user ----

    def create_user(self, username: str, password_hash: str,
                    role: str = "user", display_name: str = "") -> int:
        sql = ("INSERT INTO app_user (username, password_hash, role, display_name) "
               "VALUES (?, ?, ?, ?)")
        with self._connect() as conn:
            cur = conn.execute(sql, (username, password_hash, role, display_name))
            return cur.lastrowid

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM app_user WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM app_user WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def update_user_login(self, user_id: int) -> bool:
        now = "datetime('now', 'localtime')"
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE app_user SET last_login_at = {now} WHERE id = ?",
                (user_id,))
            return cur.rowcount > 0

    def change_user_password(self, user_id: int, password_hash: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE app_user SET password_hash = ? WHERE id = ?",
                (password_hash, user_id))
            return cur.rowcount > 0

    def set_user_status(self, user_id: int, status: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE app_user SET status = ? WHERE id = ?",
                (status, user_id))
            return cur.rowcount > 0

    def set_user_role(self, user_id: int, role: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE app_user SET role = ? WHERE id = ?",
                (role, user_id))
            return cur.rowcount > 0

    def set_user_display_name(self, user_id: int, display_name: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE app_user SET display_name = ? WHERE id = ?",
                (display_name, user_id))
            return cur.rowcount > 0

    def list_users(self, keyword: str = "", limit: int = 50, offset: int = 0) -> list[dict]:
        """分页列出用户（管理员）。支持按 username/display_name 模糊搜索。"""
        sql = "SELECT * FROM app_user"
        params: list = []
        if keyword:
            sql += " WHERE username LIKE ? OR display_name LIKE ?"
            params += [f"%{keyword}%", f"%{keyword}%"]
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ---- user_profile ----

    def get_user_profile(self, user_id: Optional[int] = None) -> Optional[dict]:
        """读取用户画像。user_id=None 时取最近一条（兼容匿名/历史数据）。"""
        with self._connect() as conn:
            if user_id is None:
                row = conn.execute(
                    "SELECT * FROM user_profile ORDER BY id DESC LIMIT 1").fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM user_profile WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                    (user_id,)).fetchone()
        return dict(row) if row else None

    def upsert_user_profile(self, budget: float = 0,
                            budget_min: float = 0,
                            flavor_preferences: str = "",
                            dietary_restrictions: str = "",
                            health_goals: str = "",
                            user_id: Optional[int] = None) -> int:
        """保存/更新用户画像。
        仅更新传入的非空字段；空字段保留原值，避免部分更新时丢数据。
        user_id 指定时按用户 upsert；为 None 时兼容旧逻辑（最近一条）。"""
        existing = self.get_user_profile(user_id=user_id)
        now = "datetime('now', 'localtime')"
        if existing:
            # 合并：只覆盖非空入参，其余保留已有值
            merged = dict(existing)
            for key, val in [("budget", budget),
                             ("budget_min", budget_min),
                             ("flavor_preferences", flavor_preferences),
                             ("dietary_restrictions", dietary_restrictions),
                             ("health_goals", health_goals)]:
                if val not in (None, "", 0):
                    merged[key] = val
            sql = f"""UPDATE user_profile SET
                      budget = ?, budget_min = ?, flavor_preferences = ?,
                      dietary_restrictions = ?, health_goals = ?, updated_at = {now}
                      WHERE id = ?"""
            with self._connect() as conn:
                conn.execute(sql, (merged["budget"], merged.get("budget_min") or 0,
                                   merged["flavor_preferences"],
                                   merged["dietary_restrictions"], merged["health_goals"],
                                   existing["id"]))
                return existing["id"]
        else:
            sql = """INSERT INTO user_profile
                     (budget, budget_min, flavor_preferences, dietary_restrictions, health_goals, user_id)
                     VALUES (?, ?, ?, ?, ?, ?)"""
            with self._connect() as conn:
                cur = conn.execute(sql, (budget, budget_min, flavor_preferences,
                                         dietary_restrictions, health_goals, user_id))
                return cur.lastrowid

    def update_nutrition_summary(self, summary_json: str,
                                 user_id: Optional[int] = None) -> bool:
        existing = self.get_user_profile(user_id=user_id)
        if not existing:
            return False
        now = "datetime('now', 'localtime')"
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE user_profile SET nutrition_summary = ?, updated_at = {now} WHERE id = ?",
                (summary_json, existing["id"]))
            return cur.rowcount > 0

    # ---- weather ----

    def get_dishes_by_weather_tag(self, weather_type: str) -> list[dict]:
        """按天气类型推荐菜品：从 weather_food_map.csv 读取标签映射。
        weather_type: cold(天冷→热汤/炖菜/热饮) / hot(天热→凉菜/清淡/水果)
        匹配 dish 的 flavor_tags(口味标签) 或 category(类别)。"""
        tags = self._weather_tags(weather_type)
        if not tags:
            return []
        clauses, params = [], []
        for field, keyword in tags:
            if field == "category":
                clauses.append("category = ?")
            else:
                clauses.append("flavor_tags LIKE ?")
                keyword = f"%{keyword}%"
            params.append(keyword)
        sql = f"SELECT * FROM dish WHERE {' OR '.join(clauses)} ORDER BY id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        seen, unique = set(), []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(dict(r))
        return unique

    def _weather_tags(self, weather_type: str) -> list[tuple]:
        """从 weather_food_map.csv 读取 (match_field, keyword) 列表。"""
        map_path = os.path.join(os.path.dirname(SCHEMA_PATH), "..", "data",
                                "weather_food_map.csv")
        tags = []
        if not os.path.exists(map_path):
            return tags
        import csv
        with open(map_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("weather_type") == weather_type and row.get("keyword"):
                    tags.append((row["match_field"], row["keyword"]))
        return tags

    # ---- v1.3 chat（历史对话） ----

    def _ensure_chat_session(self, session_id: str,
                             user_id: Optional[int] = None,
                             title: str = "") -> int:
        """确保会话记录存在，返回 chat_session.id。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM chat_session WHERE session_id = ?",
                (session_id,)).fetchone()
            if row:
                now = "datetime('now','localtime')"
                conn.execute(
                    f"UPDATE chat_session SET updated_at = {now} WHERE id = ?",
                    (row["id"],))
                return row["id"]
            cur = conn.execute(
                "INSERT INTO chat_session (session_id, title, user_id) VALUES (?, ?, ?)",
                (session_id, title[:50], user_id))
            return cur.lastrowid

    def add_chat_message(self, session_id: str, role: str, content: str,
                         user_id: Optional[int] = None) -> int:
        """追加一条对话消息。role: user / assistant。"""
        self._ensure_chat_session(session_id, user_id=user_id)
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO chat_message (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content))
            return cur.lastrowid

    def get_chat_messages(self, session_id: str) -> list[dict]:
        """按时间顺序返回会话全部消息。"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM chat_message "
                "WHERE session_id = ? ORDER BY id",
                (session_id,)).fetchall()
        return [dict(r) for r in rows]

    def list_chat_sessions(self, user_id: Optional[int] = None,
                           limit: int = 50) -> list[dict]:
        """列出历史会话（按更新时间倒序）。user_id=None 时返回全部（游客/历史）。"""
        with self._connect() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT session_id, title, created_at, updated_at "
                    "FROM chat_session ORDER BY updated_at DESC LIMIT ?",
                    (limit,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT session_id, title, created_at, updated_at "
                    "FROM chat_session WHERE user_id = ? "
                    "ORDER BY updated_at DESC LIMIT ?",
                    (user_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def delete_chat_session(self, session_id: str,
                            user_id: Optional[int] = None) -> bool:
        """删除会话（含消息）。user_id 用于越权校验；None 时任意删。"""
        with self._connect() as conn:
            if user_id is None:
                cur = conn.execute(
                    "DELETE FROM chat_session WHERE session_id = ?",
                    (session_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM chat_session WHERE session_id = ? AND user_id = ?",
                    (session_id, user_id))
            return cur.rowcount > 0


# =============================================================================
# 工厂函数
# =============================================================================

_db_instance: Optional[DatabaseInterface] = None


def get_db() -> DatabaseInterface:
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLiteDatabase()
    return _db_instance


def init_db():
    get_db().init_db()