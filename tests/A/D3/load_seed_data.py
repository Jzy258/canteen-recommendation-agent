"""
A · D3 模拟摄入数据导入脚本（供 C 测试使用）

数据源：tests/A/D3/seed_meal_records.csv（5天×3餐，共55条已确认记录）

用法（在项目根目录）：
    uv run --directory "D:\\canteen recommendation agent" python tests/A/D3/load_seed_data.py [db_path]

不带参数则写入临时数据库并打印汇总；带参数则写入指定数据库文件。
"""
import csv
import os
import sys

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))

from db import SQLiteDatabase


SEED_CSV = os.path.join(os.path.dirname(__file__), "seed_meal_records.csv")


def load_seed(db_path: str) -> dict:
    """将 seed_meal_records.csv 导入指定数据库，返回统计信息。"""
    db = SQLiteDatabase(db_path)
    db.init_db()

    # 先导入菜品库，保证 meal_record 外键可解析
    dishes_csv = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
    with open(dishes_csv, encoding="utf-8") as f:
        db.bulk_insert_dishes(list(csv.DictReader(f)))

    with open(SEED_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    stats = {"inserted": 0, "confirmed": 0, "dates": set()}
    for r in rows:
        rid = db.add_meal_record(r["date"], r["meal_time"], int(r["dish_id"]),
                                 float(r["portion"]))
        if r["confirmed"] == "1":
            db.confirm_meal_record(rid)
            stats["confirmed"] += 1
        stats["inserted"] += 1
        stats["dates"].add(r["date"])
    return stats


def print_summary(db_path: str):
    db = SQLiteDatabase(db_path)
    print("=" * 50)
    print("模拟摄入数据汇总")
    print("=" * 50)
    for d in sorted(db.get_weekly_nutrition("2026-08-01", "2026-08-31"),
                    key=lambda x: x["date"]):
        print(f"  {d['date']}: 热量{d['total_calories']}kcal "
              f"蛋白质{d['total_protein']}g 碳水{d['total_carbs']}g 脂肪{d['total_fat']}g")
    summary = db.get_weekly_summary("2026-08-01", "2026-08-31")
    if summary:
        print(f"\n  周汇总: 热量{summary['total_calories']}kcal "
              f"蛋白质{summary['total_protein']}g 碳水{summary['total_carbs']}g "
              f"脂肪{summary['total_fat']}g, {summary['day_count']}天{summary['dish_count']}菜")
    trend = db.get_weekly_trend(end_date="2026-08-07", days=7)
    print(f"\n  近7天趋势（补零）:")
    for t in trend:
        print(f"    {t['date']}: {t['total_calories']}kcal")


if __name__ == "__main__":
    import tempfile
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = os.path.join(tempfile.gettempdir(), "seed_demo.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    stats = load_seed(db_path)
    print(f"导入 {stats['inserted']} 条, 确认 {stats['confirmed']} 条, "
          f"覆盖 {len(stats['dates'])} 天: {sorted(stats['dates'])}")
    print_summary(db_path)