"""C · D2 阶段：核心流程用例（6 组 ≥ 5）

覆盖：T1 系统健康/版本、T2 菜品查询、T3 推荐+理由、T4 记录摄入(HITL)、
      T5 营养趋势、T6 异常兜底。

自包含：使用临时 SQLite + 真实后端模块（db / tools），无需 LLM 或外部服务。
运行：python tests/c/D2/test_core_flows.py
"""
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND = str(Path(__file__).parents[3] / "backend")
DATA_DIR = str(Path(__file__).parents[3] / "backend" / "data")

# 必须先于 import db 设置 DB_PATH，指向临时库
_tmp = tempfile.mktemp(suffix=".db", prefix="canteen_c_d2_")
os.environ["DB_PATH"] = _tmp
sys.path.insert(0, BACKEND)

from db import get_db  # noqa: E402
from tools.search import search_dish, get_all_dishes  # noqa: E402
from tools.scoring import recommend, score_dish  # noqa: E402
from tools.record import (  # noqa: E402
    record_meal, confirm_record, reject_record,
    get_pending_records, get_daily_intake, get_weekly_trend,
    get_weekly_summary,
)
from version import VERSION  # noqa: E402


def _seed():
    db = get_db()
    db.init_db()
    with open(os.path.join(DATA_DIR, "dishes.csv"), encoding="utf-8") as f:
        dishes = list(csv.DictReader(f))
    db.bulk_insert_dishes(dishes)
    return db


db = _seed()


# ============================================================
# T1 系统健康 / 版本
# ============================================================
def test_t1_health_and_version():
    assert VERSION, "version 为空"
    assert VERSION.count(".") == 2, f"版本号格式非法: {VERSION}"
    assert len(db.get_all_dishes()) >= 50, "种子数据 < 50 道菜"
    print(f"  VERSION={VERSION}, 种子菜品={len(db.get_all_dishes())} 道")


# ============================================================
# T2 菜品查询（对应：'有什么菜？' / '查一下红烧肉'）
# ============================================================
def test_t2_dish_query():
    # 查全部
    all_d = get_all_dishes.invoke({})
    assert len(all_d) >= 50
    d = all_d[0]
    for k in ["name", "calories", "protein", "carbs", "fat", "price", "category"]:
        assert k in d, f"菜品缺字段 {k}"
    print(f"  get_all_dishes: {len(all_d)} 道，字段完整")

    # 关键词查询：'查一下红烧肉'
    r = search_dish.invoke({"keyword": "红烧"})
    assert len(r) >= 1
    assert any("红烧" in x["name"] for x in r)
    assert float(r[0]["calories"]) > 0, "营养值缺失"
    print(f"  搜索'红烧': {[x['name'] for x in r]}")

    # 不存在的菜 → 空列表（扩展场景）
    r = search_dish.invoke({"keyword": "不存在的菜"})
    assert r == []
    print("  搜索不存在菜品 → 空列表")


# ============================================================
# T3 推荐 + 理由（对应：'10块钱预算推荐几个菜'）
# ============================================================
def test_t3_recommend_with_reason():
    r = recommend.invoke({"budget": 10, "preferences": "清淡", "health_goals": "控油", "top_k": 3})
    assert len(r) == 3
    for d in r:
        assert float(d["price"]) <= 10, f"超出预算: {d['name']} {d['price']}"
        assert 0 <= d["score"] <= 1
        for k in ["score", "budget_score", "nutrition_score", "preference_score"]:
            assert k in d, f"缺评分分项 {k}"
    # 按分降序
    assert r[0]["score"] >= r[-1]["score"]
    # 依据分项生成推荐理由（LLM 生成自由文本，测试验证理由素材齐全）
    top = r[0]
    reasons = []
    if top["budget_score"] >= 0.9:
        reasons.append("价格在预算内")
    if top["nutrition_score"] >= 0.5:
        reasons.append("营养均衡（控油导向）")
    if top["preference_score"] >= 0.6:
        reasons.append("符合口味偏好")
    assert reasons, "至少应能生成一条推荐理由"
    print(f"  推荐(预算10/清淡/控油): {[d['name'] for d in r]}")
    print(f"  理由示例: {top['name']} → {'；'.join(reasons)}")


# ============================================================
# T4 记录摄入 HITL（记录 → 待确认 → 确认 → 营养聚合）
# ============================================================
def test_t4_record_hitl():
    dish = db.get_dish_by_name("红烧肉")
    assert dish, "测试菜不存在"

    rid = record_meal.invoke({"date": "2026-08-03", "meal_time": "lunch",
                              "dish_id": dish["id"], "portion": 1.0})
    assert rid > 0

    pending = get_pending_records.invoke({})
    assert any(p["id"] == rid and p["confirmed"] == 0 for p in pending)
    print(f"  待确认记录: id={rid}, dish={dish['name']}")

    ok = confirm_record.invoke({"record_id": rid})
    assert ok is True

    daily = get_daily_intake.invoke({"date": "2026-08-03"})
    assert len(daily) >= 1
    assert daily[0]["total_calories"] == 500.0, f"营养聚合异常: {daily}"
    print(f"  确认后日营养: 午餐 {daily[0]['total_calories']} kcal")

    # 拒绝一条记录 → 不计入聚合
    rid2 = record_meal.invoke({"date": "2026-08-03", "meal_time": "dinner",
                               "dish_id": dish["id"], "portion": 1.0})
    reject_record.invoke({"record_id": rid2})
    daily = get_daily_intake.invoke({"date": "2026-08-03"})
    total_dinner = [x for x in daily if x["meal_time"] == "dinner"]
    assert not total_dinner, "被拒记录不应计入营养聚合"
    print("  被拒记录不计入聚合")


# ============================================================
# T5 营养趋势（对应：'最近7天营养摄入趋势'）
# ============================================================
def test_t5_weekly_trend():
    trend = get_weekly_trend.invoke({"end_date": "2026-08-03", "days": 7})
    assert len(trend) == 7, "应返回连续 7 天"
    dates = [x["date"] for x in trend]
    assert dates[0] == "2026-07-28" and dates[-1] == "2026-08-03", f"窗口错误: {dates}"
    # 有记录的天带数值，缺失天补零
    aug3 = trend[-1]
    assert aug3["total_calories"] == 500.0, f"8-03 应含确认记录热量: {aug3}"
    assert all(x["total_calories"] >= 0 for x in trend)
    print(f"  7 天趋势: {dates[0]}~{dates[-1]}, 8-03={aug3['total_calories']} kcal")

    summary = get_weekly_summary.invoke({"start_date": "2026-07-28", "end_date": "2026-08-03"})
    assert summary and summary.get("day_count", 0) >= 1
    assert summary["total_calories"] == 500.0
    print(f"  周汇总: {summary['day_count']} 天 / {summary['dish_count']} 菜")


# ============================================================
# T6 异常兜底（空/非法输入不崩，返回中性或空结果）
# ============================================================
def test_t6_edge_cases():
    # recommend 非法参数回落默认
    r = recommend.invoke({"budget": -5, "top_k": 0})
    assert len(r) == 5, "非法参数应回落默认"
    print("  recommend(budget=-5, top_k=0) → 回落默认 5 条")

    # 超小预算（可能无解）不抛异常
    r = recommend.invoke({"budget": 0.01, "top_k": 3})
    assert isinstance(r, list)
    print(f"  recommend(budget=0.01) → {len(r)} 条（不崩溃）")

    # score_dish 空输入 → 零分不抛
    s = score_dish(None, None)
    assert s["score"] >= 0
    print("  score_dish(None) → 中性分")

    # 搜索特殊字符 → 空列表
    r = search_dish.invoke({"keyword": "!@#$"})
    assert r == []
    print("  搜索特殊字符 → 空列表")


def run_all():
    tests = [
        ("T1 健康/版本", test_t1_health_and_version),
        ("T2 菜品查询", test_t2_dish_query),
        ("T3 推荐+理由", test_t3_recommend_with_reason),
        ("T4 记录摄入HITL", test_t4_record_hitl),
        ("T5 营养趋势", test_t5_weekly_trend),
        ("T6 异常兜底", test_t6_edge_cases),
    ]
    passed = 0
    print("=" * 50)
    for name, t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            import traceback
            print(f"  FAIL: {name} - {e}")
            traceback.print_exc()
        print("-" * 50)
    print(f"\n{passed}/{len(tests)} 组核心流程用例通过")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
