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
    def get_records_by_date(self, date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_daily_nutrition(self, date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_day_total(self, date: str) -> Optional[dict]:
        ...

    @abstractmethod
    def get_weekly_nutrition(self, start_date: str, end_date: str) -> list[dict]:
        ...

    @abstractmethod
    def get_weekly_summary(self, start_date: str, end_date: str) -> Optional[dict]:
        ...

    @abstractmethod
    def get_weekly_trend(self, end_date: str = "", days: int = 7) -> list[dict]:
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
            ok = cur.rowcount > 0
        if ok:
            self._refresh_profile_summary()
        return ok

    def reject_meal_record(self, record_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE meal_record SET confirmed = -1 WHERE id = ? AND confirmed = 0",
                (record_id,))
            return cur.rowcount > 0

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
        if n > 0:
            self._refresh_profile_summary()
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

    def _refresh_profile_summary(self):
        """确认记录后，重算已确认记录的历史营养汇总并写入 user_profile。
        汇总内容：总摄入、日均营养、按餐次平均、菜品多样性、近7天趋势。"""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT
                       COUNT(*) AS record_count,
                       COUNT(DISTINCT date) AS day_count,
                       COUNT(DISTINCT d.id) AS dish_kind_count,
                       ROUND(SUM(d.calories * mr.portion), 1) AS total_calories,
                       ROUND(SUM(d.protein * mr.portion), 1) AS total_protein,
                       ROUND(SUM(d.carbs * mr.portion), 1) AS total_carbs,
                       ROUND(SUM(d.fat * mr.portion), 1) AS total_fat
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 1""").fetchone()

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
            summary["meal_averages"] = self._meal_averages()
            summary["recent_trend"] = self._recent_trend()

        import json
        if self.get_user_profile() is None:
            self.upsert_user_profile()
        self.update_nutrition_summary(json.dumps(summary, ensure_ascii=False))

    def _meal_averages(self) -> dict:
        """按餐次统计平均摄入。"""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT mr.meal_time,
                          ROUND(SUM(d.calories * mr.portion) / COUNT(DISTINCT mr.date), 1) AS avg_calories
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 1
                   GROUP BY mr.meal_time""").fetchall()
        return {r["meal_time"]: r["avg_calories"] for r in rows}

    def _recent_trend(self, days: int = 7) -> list[dict]:
        """最近 N 天每日热量摄入（仅含实际有记录的天）。"""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT mr.date,
                          ROUND(SUM(d.calories * mr.portion), 1) AS calories
                   FROM meal_record mr JOIN dish d ON mr.dish_id = d.id
                   WHERE mr.confirmed = 1
                   GROUP BY mr.date
                   ORDER BY mr.date DESC LIMIT ?""",
                (days,)).fetchall()
        return [dict(r) for r in reversed(rows)]

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

    def get_day_total(self, date: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM v_day_total WHERE date = ?",
                (date,)).fetchone()
        return dict(row) if row else None

    def get_weekly_nutrition(self, start_date: str, end_date: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM v_weekly_nutrition WHERE date BETWEEN ? AND ? ORDER BY date",
                (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]

    def get_weekly_summary(self, start_date: str, end_date: str) -> Optional[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM v_week_summary WHERE start_date >= ? AND end_date <= ?",
                (start_date, end_date)).fetchall()
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

    def get_weekly_trend(self, end_date: str = "", days: int = 7) -> list[dict]:
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
            rows = conn.execute(
                "SELECT * FROM v_day_total WHERE date BETWEEN ? AND ? ORDER BY date",
                (start.isoformat(), end.isoformat())).fetchall()

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
        """保存/更新用户画像。
        仅更新传入的非空字段；空字段保留原值，避免部分更新时丢数据。
        """
        existing = self.get_user_profile()
        now = "datetime('now', 'localtime')"
        if existing:
            # 合并：只覆盖非空入参，其余保留已有值
            merged = dict(existing)
            for key, val in [("budget", budget),
                             ("flavor_preferences", flavor_preferences),
                             ("dietary_restrictions", dietary_restrictions),
                             ("health_goals", health_goals)]:
                if val not in (None, "", 0):
                    merged[key] = val
            sql = f"""UPDATE user_profile SET
                      budget = ?, flavor_preferences = ?, dietary_restrictions = ?,
                      health_goals = ?, updated_at = {now}
                      WHERE id = ?"""
            with self._connect() as conn:
                conn.execute(sql, (merged["budget"], merged["flavor_preferences"],
                                   merged["dietary_restrictions"], merged["health_goals"],
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