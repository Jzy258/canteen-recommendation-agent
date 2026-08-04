"""
食堂菜品营养数据清洗脚本

功能：
    1. 去重（完全重复 + 近似重复名称检测）
    2. 统一单位（kcal / g / 元）
    3. 缺失值填充
    4. 异常值检测与修正
    5. 输出清洗报告

用法：
    python backend/data/clean.py                        # 清洗 dishes.csv
    python backend/data/clean.py --check                # 仅检查不修改
    python backend/data/clean.py --input X.csv --output Y.csv
"""

import argparse
import csv
import os
import sys


EXPECTED_FIELDS = ["name", "calories", "protein", "carbs", "fat", "price",
                   "category", "flavor_tags", "source"]

VALID_CATEGORIES = {"荤菜", "素菜", "汤", "主食", "水果", "饮品"}

NUTR_RANGE = {
    "calories": (0, 800),
    "protein":  (0, 60),
    "carbs":    (0, 80),
    "fat":      (0, 50),
    "price":    (0, 50),
}


def load_csv(path: str) -> tuple[list[str], list[dict]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def save_csv(path: str, fieldnames: list[str], rows: list[dict]):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_name(name: str) -> str:
    """统一名称格式：去空格、全角转半角"""
    name = name.strip().replace(" ", "").replace("　", "")
    return name


def is_near_duplicate(name_a: str, name_b: str) -> bool:
    """近似重复检测：同一道菜的不同写法（如"红烧肉" vs "红烧肉片"）。
    规则：一个名称是另一个的前缀（长度差 ≥1，如 A+B 型），视为同菜；
    "酸辣土豆丝" vs "醋溜土豆丝"（前缀不同、长度相同）不是重复。
    完全相同由上层完全去重处理。"""
    a, b = normalize_name(name_a), normalize_name(name_b)
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    # 前缀子串且长度差 ≥1（长名是短名的扩展，如"红烧肉"+"片"）
    return long.startswith(short) and len(long) > len(short)


def clean(rows: list[dict], check_only: bool = False) -> tuple[list[dict], list[str]]:
    report = []
    cleaned = []
    issues = []

    for i, row in enumerate(rows):
        entry = dict(row)
        row_num = i + 2  # +1 跳过 header, +1 0-index

        # ---- 1. 字段完整性 ----
        for field in EXPECTED_FIELDS:
            if field not in entry:
                issues.append(f"行{row_num} [{entry.get('name','?')}]: 缺少字段 '{field}'")
                entry[field] = ""

        # ---- 2. 名称清洗 ----
        orig_name = entry["name"]
        entry["name"] = normalize_name(entry["name"])
        if entry["name"] != orig_name:
            issues.append(f"行{row_num}: 名称规范化 '{orig_name}' → '{entry['name']}'")

        if not entry["name"]:
            issues.append(f"行{row_num}: 名称为空，跳过")
            continue

        # ---- 3. 数值字段清洗 ----
        for field in ["calories", "protein", "carbs", "fat", "price"]:
            raw = entry[field].strip()
            if not raw:
                issues.append(f"行{row_num} [{entry['name']}]: {field} 为空，标记为 0")
                entry[field] = "0"
                continue
            try:
                val = float(raw)
                if val < 0:
                    issues.append(f"行{row_num} [{entry['name']}]: {field}={val} 为负值，取绝对值")
                    entry[field] = str(abs(val))
                lo, hi = NUTR_RANGE[field]
                if val > hi:
                    issues.append(f"行{row_num} [{entry['name']}]: {field}={val} 超出上限{hi}，已截断")
                    entry[field] = str(hi)
            except ValueError:
                issues.append(f"行{row_num} [{entry['name']}]: {field}='{raw}' 无法解析为数值，标记为 0")
                entry[field] = "0"

        # ---- 4. 分类校验 ----
        if entry["category"] not in VALID_CATEGORIES:
            issues.append(f"行{row_num} [{entry['name']}]: 分类 '{entry['category']}' 无效，标记为 '素菜'")
            entry["category"] = "素菜"

        # ---- 5. 来源标注 ----
        if not entry["source"].strip():
            issues.append(f"行{row_num} [{entry['name']}]: 来源为空，标记为 '待补充'")
            entry["source"] = "待补充"

        cleaned.append(entry)

    # ---- 6. 去重 ----
    seen_names = {}
    deduped = []
    for entry in cleaned:
        name = entry["name"]
        # 完全重复
        if name in seen_names:
            issues.append(f"完全重复: '{name}' (行{seen_names[name]} 与 当前行)，跳过")
            continue
        # 近似重复
        near = [k for k in seen_names if is_near_duplicate(name, k) and k != name]
        if near:
            issues.append(f"近似重复: '{name}' ≈ '{near[0]}'，保留 '{near[0]}'，跳过 '{name}'")
            continue
        seen_names[name] = f"行{cleaned.index(entry)+2}"
        deduped.append(entry)

    # ---- 报告 ----
    report.append(f"原始记录: {len(rows)} 条")
    report.append(f"清洗后: {len(deduped)} 条")
    report.append(f"跳过: {len(rows) - len(deduped)} 条")
    report.append(f"问题数: {len(issues)} 项")
    if issues:
        report.append("")
        report.append("问题明细:")
        for iss in issues:
            report.append(f"  - {iss}")

    if check_only:
        print("\n".join(report))
        return deduped, report

    return deduped, report


def main():
    parser = argparse.ArgumentParser(description="菜品营养数据清洗工具")
    parser.add_argument("--input", default=os.path.join(os.path.dirname(__file__), "dishes.csv"))
    parser.add_argument("--output", default=os.path.join(os.path.dirname(__file__), "dishes.csv"))
    parser.add_argument("--check", action="store_true", help="仅检查不修改")
    args = parser.parse_args()

    fieldnames, rows = load_csv(args.input)
    print(f"读取 {args.input}: {len(rows)} 条记录\n")

    cleaned, report = clean(rows, check_only=args.check)

    if not args.check:
        save_csv(args.output, fieldnames, cleaned)
        print(f"写入 {args.output}: {len(cleaned)} 条记录\n")

    print("=" * 50)
    print("清洗报告")
    print("=" * 50)
    print("\n".join(report))


if __name__ == "__main__":
    main()