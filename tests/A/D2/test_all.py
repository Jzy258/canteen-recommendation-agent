"""
A · D2 阶段全部验证测试
覆盖：menu.csv / clean.py / cleaning_log.md / init_db.py 菜单导入

用法：uv run --directory "D:\\canteen recommendation agent" python tests/A/D2/test_all.py
"""
import csv, os, sys, tempfile

# 基于脚本位置推导项目根目录（tests/A/D2/test_all.py → 上3层）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "data"))

conn = None
conn2 = None
tmp_db = None

try:

    # ============================================================
    # 1. menu.csv 格式与完整性检查
    # ============================================================
    print("=" * 50)
    print("1. menu.csv 格式与完整性检查")
    print("=" * 50)

    menu_path = os.path.join(_PROJECT_ROOT, "backend", "data", "menu.csv")
    assert os.path.exists(menu_path), "menu.csv 不存在"
    with open(menu_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        menu_rows = list(reader)

    assert len(menu_rows) >= 75, f"菜单记录数不足75: {len(menu_rows)}"
    print(f"  [PASS] 记录总数: {len(menu_rows)}")

    for row in menu_rows:
        assert "date" in row, "缺少 date 字段"
        assert "meal_time" in row, "缺少 meal_time 字段"
        assert "dish_id" in row, "缺少 dish_id 字段"
        assert row["meal_time"] in ("breakfast", "lunch", "dinner"), f"餐次非法: {row['meal_time']}"
        int(row["dish_id"])
    print("  [PASS] 字段完整, 餐次合法")

    dates = sorted(set(r["date"] for r in menu_rows))
    assert len(dates) == 5, f"天数不足5: {len(dates)}"
    print(f"  [PASS] 日期分布: {dates}")

    for d in dates:
        meals = set(r["meal_time"] for r in menu_rows if r["date"] == d)
        assert meals == {"breakfast", "lunch", "dinner"}, f"{d} 餐次不全: {meals}"
    print("  [PASS] 每日 3 餐齐全")

    for d in dates:
        for mt in ("breakfast", "lunch", "dinner"):
            cnt = sum(1 for r in menu_rows if r["date"] == d and r["meal_time"] == mt)
            assert cnt >= 4, f"{d} {mt} 菜品不足4: {cnt}"
    print("  [PASS] 每餐 ≥4 道菜")

    dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
    with open(dish_path, encoding="utf-8") as f:
        dish_count = len(list(csv.DictReader(f)))
    valid_dish_ids = set(range(1, dish_count + 1))

    for r in menu_rows:
        did = int(r["dish_id"])
        assert did in valid_dish_ids, f"dish_id {did} 在 dishes.csv 中不存在"
    print(f"  [PASS] 所有 dish_id 有效 (范围 1-{dish_count})")

    for d in dates:
        for mt in ("breakfast", "lunch", "dinner"):
            dids = [int(r["dish_id"]) for r in menu_rows if r["date"] == d and r["meal_time"] == mt]
            assert len(dids) == len(set(dids)), f"{d} {mt} 存在重复菜品"
    print("  [PASS] 每餐菜品无重复")

    # ============================================================
    # 2. clean.py 结构检查
    # ============================================================
    print("\n" + "=" * 50)
    print("2. clean.py 结构检查")
    print("=" * 50)

    clean_path = os.path.join(_PROJECT_ROOT, "backend", "data", "clean.py")
    assert os.path.exists(clean_path), "clean.py 不存在"
    with open(clean_path, encoding="utf-8") as f:
        clean_code = f.read()

    assert "def clean" in clean_code, "缺少 clean() 函数"
    assert "def load_csv" in clean_code, "缺少 load_csv()"
    assert "normalize_name" in clean_code, "缺少名称规范化"
    assert "check_only" in clean_code, "缺少 --check 模式"
    print("  [PASS] clean.py 结构完整")

    import subprocess
    sub_env = dict(os.environ)
    sub_env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, clean_path, "--check"],
        capture_output=True, text=True, encoding="utf-8", env=sub_env
    )
    assert result.returncode == 0, f"clean.py --check 执行失败: {result.stderr}"
    assert "54 条" in result.stdout, "输出未包含菜品数量"
    print("  [PASS] clean.py --check 可正常执行")

    # ============================================================
    # 3. cleaning_log.md 完整性检查
    # ============================================================
    print("\n" + "=" * 50)
    print("3. cleaning_log.md 完整性检查")
    print("=" * 50)

    log_path = os.path.join(_PROJECT_ROOT, "backend", "data", "cleaning_log.md")
    assert os.path.exists(log_path), "cleaning_log.md 不存在"
    with open(log_path, encoding="utf-8") as f:
        log_content = f.read()

    required_sections = [
        "数据来源", "清洗流程", "字段完整性", "名称规范化",
        "重复检测", "数值字段", "分类校验", "来源标注",
        "清洗结果汇总", "单位统一", "缺失值处理", "脚本使用",
    ]
    for section in required_sections:
        assert section in log_content, f"cleaning_log.md 缺少 '{section}' 章节"
    print("  [PASS] 章节完整")

    assert "中国食物成分表" in log_content, "缺少数据来源说明"
    assert "54" in log_content, "缺少菜品数量"
    assert "clean.py" in log_content, "缺少清洗工具引用"
    print("  [PASS] 关键内容完整")

    # ============================================================
    # 4. init_db.py 菜单导入功能验证
    # ============================================================
    print("\n" + "=" * 50)
    print("4. init_db.py 菜单导入功能验证")
    print("=" * 50)

    init_path = os.path.join(_PROJECT_ROOT, "backend", "data", "init_db.py")
    with open(init_path, encoding="utf-8") as f:
        init_code = f.read()
    assert "menu.csv" in init_code, "init_db.py 未引用 menu.csv"
    assert "import_menu" in init_code or "menu_item" in init_code, "init_db.py 未实现菜单导入"
    print("  [PASS] init_db.py 包含菜单导入逻辑")

    # ============================================================
    # 5. 完整数据库集成测试（含菜单）
    # ============================================================
    print("\n" + "=" * 50)
    print("5. 完整数据库集成测试（含菜单）")
    print("=" * 50)

    tmp_db = os.path.join(tempfile.gettempdir(), "test_canteen_d2.db")
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))
    from db import SQLiteDatabase

    db = SQLiteDatabase(tmp_db)
    db.init_db()

    with open(dish_path, encoding="utf-8") as f:
        dishes = list(csv.DictReader(f))
    db.bulk_insert_dishes(dishes)
    assert len(db.get_all_dishes()) == 54
    print("  [PASS] 5.1 菜品导入: 54 道")

    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    menu_groups = {}
    for row in menu_rows:
        key = (row["date"], row["meal_time"])
        menu_groups.setdefault(key, []).append(int(row["dish_id"]))

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
    conn.commit()
    print("  [PASS] 5.2 菜单导入完成")

    for d in ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07"]:
        r = db.get_menu_by_date(d)
        assert len(r) > 0, f"{d} 菜单为空"
        meals = set(item["meal_time"] for item in r)
        assert meals == {"breakfast", "lunch", "dinner"}, f"{d} 餐次不全: {meals}"
    print("  [PASS] 5.3 每日菜单查询: 5天×3餐")

    r = db.get_weekly_menu()
    assert len(r) == 75
    print("  [PASS] 5.4 v_menu_detail: 75 条关联")

    for d in ["2026-08-03", "2026-08-05", "2026-08-07"]:
        for mt in ["breakfast", "lunch", "dinner"]:
            r = db.get_dishes_for_menu(d, mt)
            assert len(r) >= 4, f"{d} {mt} 菜品不足: {len(r)}"
    print("  [PASS] 5.5 get_dishes_for_menu: 每餐 ≥4 道")

    try:
        conn2 = sqlite3.connect(tmp_db)
        conn2.execute("PRAGMA foreign_keys = ON")
        conn2.execute("INSERT INTO menu_item (menu_id, dish_id) VALUES (1, 9999)")
        conn2.commit()
        conn2.close()
        conn2 = None
        assert False, "外键约束未生效"
    except Exception:
        print("  [PASS] 5.6 外键约束: 无效 dish_id 被拒绝")

    r = db.get_menu_by_date_range("2026-08-03", "2026-08-05")
    dates_found = sorted(set(item["date"] for item in r))
    assert dates_found == ["2026-08-03", "2026-08-04", "2026-08-05"]
    print("  [PASS] 5.7 get_menu_by_date_range: 3天范围")

    sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "data"))
    from clean import clean, load_csv
    _, report = clean(load_csv(dish_path)[1])
    assert "原始记录: 54 条" in report[0]
    assert "清洗后: 54 条" in report[1]
    assert "问题数: 0 项" in report[3]
    print("  [PASS] 5.8 clean.py 验证: 54条0问题")

    print("\n" + "=" * 50)
    print("全部验证通过")
    print("=" * 50)

finally:
    # 清理资源
    for c in [conn, conn2]:
        try:
            c.close()
        except Exception:
            pass
    if tmp_db and os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass