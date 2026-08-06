"""将 backend/data/dishes.csv 导入数据库（INSERT OR IGNORE）。
用法：
    python backend/scripts/import_dishes.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import SQLiteDatabase

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dishes.csv')


def load_csv(path: str) -> list[dict]:
    items = []
    with open(path, encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            items.append({
                'name': row.get('name', '').strip(),
                'calories': float(row.get('calories') or 0),
                'protein': float(row.get('protein') or 0),
                'carbs': float(row.get('carbs') or 0),
                'fat': float(row.get('fat') or 0),
                'price': float(row.get('price') or 0),
                'category': (row.get('category') or '').strip(),
                'flavor_tags': (row.get('flavor_tags') or '').strip(),
                'source': (row.get('source') or '').strip(),
            })
    return items


def main():
    if not os.path.exists(CSV_PATH):
        print('CSV not found:', CSV_PATH)
        return
    dishes = load_csv(CSV_PATH)
    db = SQLiteDatabase()
    n = db.bulk_insert_dishes(dishes)
    print(f'Inserted/ignored changes (total DB changes): {n}')


if __name__ == '__main__':
    main()
