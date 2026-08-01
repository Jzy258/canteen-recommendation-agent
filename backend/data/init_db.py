"""
食堂菜品推荐与营养分析 Agent — 数据库初始化脚本

用法：
    python backend/data/init_db.py

功能：
    1. 建表（执行 backend/db/schema.sql）
    2. 从 dishes.csv 导入菜品数据
    3. 导入菜单数据（若 menu.csv 存在）
    4. 打印初始化统计
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "db"))
from db import init_db as create_tables, get_db


DATA_DIR = os.path.dirname(__file__)
DISHES_CSV = os.path.join(DATA_DIR, "dishes.csv")
MENU_CSV = os.path.join(DATA_DIR, "menu.csv")


def load_dishes(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_menu(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def import_menu(db, menu_rows: list[dict]):
    from datetime import datetime, timedelta

    menu_groups = {}
    for row in menu_rows:
        key = (row["date"], row["meal_time"])
        menu_groups.setdefault(key, []).append(int(row["dish_id"]))

    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        count = 0
        for (date, meal_time), dish_ids in menu_groups.items():
            cur = conn.execute(
                "INSERT OR IGNORE INTO menu (date, meal_time) VALUES (?, ?)",
                (date, meal_time),
            )
            menu_id = cur.lastrowid
            if menu_id == 0:
                existing = conn.execute(
                    "SELECT id FROM menu WHERE date = ? AND meal_time = ?",
                    (date, meal_time),
                ).fetchone()
                menu_id = existing["id"]
            for did in dish_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO menu_item (menu_id, dish_id) VALUES (?, ?)",
                    (menu_id, did),
                )
                count += 1
        conn.commit()
        print(f"  menu_item 关联: {count} 条")
    finally:
        conn.close()


def main():
    create_tables()
    db = get_db()

    # ---- 导入菜品 ----
    dishes = load_dishes(DISHES_CSV)
    print(f"读取菜品: {len(dishes)} 道")

    inserted = db.bulk_insert_dishes(dishes)
    print(f"新增入库: {inserted} 道 (重复已跳过)")

    total = len(db.get_all_dishes())
    print(f"累计菜品数: {total}")

    # ---- 按分类统计 ----
    all_dishes = db.get_all_dishes()
    cats = {}
    for d in all_dishes:
        cats[d["category"]] = cats.get(d["category"], 0) + 1
    print("分类分布:", dict(sorted(cats.items())))

    # ---- 导入菜单（若存在） ----
    if os.path.exists(MENU_CSV):
        import sqlite3

        menu_rows = load_menu(MENU_CSV)
        print(f"\n读取菜单: {len(menu_rows)} 条记录")
        import_menu(db, menu_rows)
    else:
        print(f"\n{MENU_CSV} 不存在，跳过菜单导入")

    print("\n初始化完成")


if __name__ == "__main__":
    main()