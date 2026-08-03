"""
A · D7 数据边界 / 异常输入 / 空结果 处理验证
覆盖：scoring / optimizer / db 对 None、非法类型、空结果、负数、非法日期的容错
"""
import csv, os, sys, tempfile

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "db"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend", "tools"))

from scoring import (
    budget_score, nutrition_score, preference_score, score_dish,
    score_dishes, recommend,
)
from optimizer import optimize_meal, optimize_meal_tool
from db import SQLiteDatabase

passes = 0
fails = 0

def check(name, cond, detail=""):
    global passes, fails
    if cond:
        passes += 1
        print(f"  [PASS] {name}")
    else:
        fails += 1
        print(f"  [FAIL] {name} {detail}")

tmp_db = None
try:

    print("=" * 55)
    print("1. scoring.py 边界容错")
    print("=" * 55)
    # 非数值价格
    check("budget_score('abc') 返回1.0", budget_score("abc", 10) == 1.0)
    check("budget_score(None) 返回1.0", budget_score(None, 10) == 1.0)
    check("budget_score(-5,10) 返回1.0", budget_score(-5, 10) == 1.0)
    # None 输入
    check("nutrition_score(None) 返回0", nutrition_score(None) == 0.0)
    check("nutrition_score({}) 返回0", nutrition_score({}) == 0.0)
    check("preference_score(None,None) 返回0.5", preference_score(None, None) == 0.5)
    check("score_dish(None,{}) 不抛异常", isinstance(score_dish(None, {}), dict))
    check("score_dishes(None,{}) 返回空", score_dishes(None, {}) == [])
    check("score_dishes([],{}) 返回空", score_dishes([], {}) == [])
    # 负热量
    bad_dish = {"category": "荤菜", "calories": -100, "protein": -5, "carbs": -1, "fat": -3}
    s = nutrition_score(bad_dish)
    check("负营养值不抛异常", 0 <= s <= 1)

    print("\n" + "=" * 55)
    print("2. recommend @tool 异常入参")
    print("=" * 55)
    # 需要临时库
    tmp_db = os.path.join(tempfile.gettempdir(), "test_d7.db")
    db = SQLiteDatabase(tmp_db)
    db.init_db()
    import db as _dbm
    _dbm._db_instance = db
    dish_path = os.path.join(_PROJECT_ROOT, "backend", "data", "dishes.csv")
    with open(dish_path, encoding="utf-8") as f:
        db.bulk_insert_dishes(list(csv.DictReader(f)))

    r_neg = recommend.invoke({"budget": -1, "top_k": 3})
    check("budget=-1 回落到默认预算", len(r_neg) >= 0)
    r_zero = recommend.invoke({"budget": 0, "top_k": 3})
    check("budget=0 使用已存画像/默认", len(r_zero) > 0, f"got {len(r_zero)}")
    r_badk = recommend.invoke({"budget": 10, "top_k": -5})
    check("top_k=-5 回落到默认5", len(r_badk) == 5)
    r_badk2 = recommend.invoke({"budget": 10, "top_k": 0})
    check("top_k=0 回落到默认5", len(r_badk2) == 5)

    print("\n" + "=" * 55)
    print("3. optimizer.py 边界容错")
    print("=" * 55)
    dishes = db.get_all_dishes()
    r_empty = optimize_meal([], 20, 800)
    check("空菜品返回空结果", r_empty["dishes"] == [] and r_empty["reason"])
    r_none = optimize_meal(None, 20, 800)
    check("None 菜品返回空结果", r_none["dishes"] == [])
    r_zero = optimize_meal(dishes, 0, 800)
    check("预算0返回空", r_zero["dishes"] == [])
    r_neg = optimize_meal(dishes, -5, 800)
    check("负预算返回空", r_neg["dishes"] == [])
    r_str = optimize_meal(dishes, "abc", 800)
    check("字符串预算返回空+原因", r_str["dishes"] == [] and r_str["reason"])
    r_cal_str = optimize_meal(dishes, 20, "bad")
    check("字符串热量返回空+原因", r_cal_str["dishes"] == [] and r_cal_str["reason"])

    print("\n" + "=" * 55)
    print("4. db.py 空结果/异常输入")
    print("=" * 55)
    check("get_dish_by_id(0) 返回None", db.get_dish_by_id(0) is None)
    check("get_dish_by_id(-1) 返回None", db.get_dish_by_id(-1) is None)
    all_count = len(db.get_all_dishes())
    check("search_dishes(None) 无过滤返回全部", len(db.search_dishes(keyword=None)) == all_count)
    check("search_dishes(max_price=-1) 无过滤返回全部",
          len(db.search_dishes(max_price=-1)) == all_count)
    check("search_dishes(不存在关键词) 返回空",
          db.search_dishes(keyword="佛跳墙") == [])
    check("get_menu_by_date('') 返回空", db.get_menu_by_date("") == [])
    check("get_records_by_date('') 返回空", db.get_records_by_date("") == [])
    check("get_weekly_nutrition('','') 返回空", db.get_weekly_nutrition("", "") == [])
    trend_bad = db.get_weekly_trend(end_date="bad-date")
    check("get_weekly_trend 非法日期回退今天", len(trend_bad) == 7)
    trend_badk = db.get_weekly_trend(days=-3)
    check("get_weekly_trend 负数天数回退7", len(trend_badk) == 7)
    check("get_dishes_by_weather_tag(None) 返回空", db.get_dishes_by_weather_tag(None) == [])
    check("get_dishes_by_weather_tag('') 返回空", db.get_dishes_by_weather_tag("") == [])

    print("\n" + "=" * 55)
    print(f"D7 边界验证: {passes} 通过, {fails} 失败")
    print("=" * 55)
    if fails == 0:
        print("D7 数据边界处理全部通过")
    else:
        print("存在失败项")
    sys.exit(1 if fails else 0)

finally:
    if tmp_db and os.path.exists(tmp_db):
        try:
            os.remove(tmp_db)
        except Exception:
            pass