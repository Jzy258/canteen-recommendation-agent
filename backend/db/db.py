import sqlite3
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional


DB_PATH = os.getenv("DB_PATH", "backend/data/canteen.db")
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
                        portion: float = 1.0) -> int:
        ...

    @abstractmethod
    def confirm_meal_record(self, record_id: int) -> bool:
        ...

    @abstractmethod
    def reject_meal_record(self, record_id: int) -> bool:
        ...

    @abstractmethod
    def get_pending_records(self) -> list[dict]:
        ...

    @abstractmethod
    def get_records_by_date(self, date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_daily_nutrition(self, date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_weekly_nutrition(self, start_date: str, end_date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_user_profile(self) -> Optional[dict]:
        ...

    @abstractmethod
    def upsert_user_profile(self, budget: float = 0,
                            flavor_preferences: str = "",
                            dietary_restrictions: str = "",
                            health_goals: str = "") -> int:
        ...

    @abstractmethod
    def update_nutrition_summary(self, summary_json: str) -> bool:
        ...

    @abstractmethod
    def get_dishes_by_weather_tag(self, weather_type: str) -> list[dict]:
        ...


# =============================================================================
# SQLite 实现
# =============================================================================

class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

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
                 (name, calories, protein, carbs, fat, price, category, flavor_tags, source)
                 VALUES (:name, :calories, :protein, :carbs, :fat, :price, :category, :flavor_tags, :source)"""
        with self._connect() as conn:
            conn.executemany(sql, dishes)
            return conn.total_changes

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

    def add_meal_record(self, date: str, meal_time: str, dish_id: int,
                        portion: float = 1.0) -> int:
        sql = """INSERT INTO meal_record (date, meal_time, dish_id, portion)
                 VALUES (?, ?, ?, ?)"""
        with self._connect() as conn:
            cur = conn.execute(sql, (date, meal_time, dish_id, portion))
            return cur.lastrowid

    def confirm_meal_record(self, record_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE meal_record SET confirmed = 1 WHERE id = ? AND confirmed = 0",
                (record_id,))
            return cur.rowcount > 0

    def reject_meal_record(self, record_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE meal_record SET confirmed = -1 WHERE id = ? AND confirmed = 0",
                (record_id,))
            return cur.rowcount > 0

    def get_pending_records(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT mr.*, d.name AS dish_name, d.calories, d.protein, d.carbs, d.fat
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 0
                   ORDER BY mr.date, mr.meal_time""").fetchall()
        return [dict(r) for r in rows]

    def get_records_by_date(self, date: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT mr.*, d.name AS dish_name, d.calories, d.protein, d.carbs, d.fat
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.date = ? AND mr.confirmed = 1
                   ORDER BY mr.meal_time""",
                (date,)).fetchall()
        return [dict(r) for r in rows]

    def get_daily_nutrition(self, date: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM v_daily_nutrition WHERE date = ? ORDER BY meal_time",
                (date,)).fetchall()
        return [dict(r) for r in rows]

    def get_weekly_nutrition(self, start_date: str, end_date: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM v_weekly_nutrition WHERE date BETWEEN ? AND ? ORDER BY date",
                (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]

    # ---- user_profile ----

    def get_user_profile(self) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_profile ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def upsert_user_profile(self, budget: float = 0,
                            flavor_preferences: str = "",
                            dietary_restrictions: str = "",
                            health_goals: str = "") -> int:
        existing = self.get_user_profile()
        now = "datetime('now', 'localtime')"
        if existing:
            sql = f"""UPDATE user_profile SET
                      budget = ?, flavor_preferences = ?, dietary_restrictions = ?,
                      health_goals = ?, updated_at = {now}
                      WHERE id = ?"""
            with self._connect() as conn:
                conn.execute(sql, (budget, flavor_preferences,
                                   dietary_restrictions, health_goals,
                                   existing["id"]))
                return existing["id"]
        else:
            sql = """INSERT INTO user_profile (budget, flavor_preferences, dietary_restrictions, health_goals)
                     VALUES (?, ?, ?, ?)"""
            with self._connect() as conn:
                cur = conn.execute(sql, (budget, flavor_preferences,
                                         dietary_restrictions, health_goals))
                return cur.lastrowid

    def update_nutrition_summary(self, summary_json: str) -> bool:
        existing = self.get_user_profile()
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
        tag_map = {
            "cold": ["热汤", "炖菜", "火锅", "热饮", "面食", "汤"],
            "hot":  ["凉菜", "清淡", "水果", "冷饮", "清蒸", "凉拌"],
        }
        tags = tag_map.get(weather_type, [])
        if not tags:
            return []
        placeholders = " OR ".join(["flavor_tags LIKE ?" for _ in tags])
        params = [f"%{t}%" for t in tags]
        sql = f"SELECT * FROM dish WHERE {placeholders} ORDER BY id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        results = [dict(r) for r in rows]
        seen = set()
        unique = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)
        return unique


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