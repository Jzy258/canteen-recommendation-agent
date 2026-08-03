import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_ROOT / "backend"))

import csv
from db import SQLiteDatabase
from store import profile as store_mod


def _setup_tmp_db():
    tmp = os.path.join(tempfile.gettempdir(), "test_store.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    real_db = SQLiteDatabase(tmp)
    real_db.init_db()
    import db.db as db_module
    db_module._db_instance = real_db
    with open(_ROOT / "backend" / "data" / "dishes.csv", encoding="utf-8") as f:
        real_db.bulk_insert_dishes(list(csv.DictReader(f)))
    import importlib
    importlib.reload(store_mod)
    return tmp


def test_save_and_get_profile():
    pid = store_mod.save_profile(budget=15, flavor_preferences="辣",
                                 dietary_restrictions="", health_goals="高蛋白")
    assert pid > 0, "should return profile id"
    p = store_mod.get_profile()
    assert p is not None
    assert p["budget"] == 15.0
    assert p["flavor_preferences"] == "辣"
    print(f"  saved profile id={pid}, budget={p['budget']}")


def test_upsert_updates():
    store_mod.save_profile(budget=15, flavor_preferences="辣", health_goals="高蛋白")
    pid2 = store_mod.save_profile(budget=20, flavor_preferences="辣", health_goals="控油")
    p = store_mod.get_profile()
    assert p["id"] == pid2, "upsert should update same row"
    assert p["budget"] == 20.0 and p["health_goals"] == "控油"
    print(f"  upsert updated: budget={p['budget']}, goal={p['health_goals']}")


def test_build_context_empty():
    ctx = store_mod.build_context()
    assert isinstance(ctx, str) and ctx
    print(f"  context: {ctx[:60]}")


def test_summarize_nutrition():
    s = store_mod.summarize_nutrition(days=7)
    assert s is not None, "should return summary"
    assert "days" in s and "avg_calories" in s
    print(f"  summary: days={s['days']}, avg_cal={s['avg_calories']}")


def test_tools_registered():
    from store.profile import set_user_profile, get_user_profile_tool
    assert set_user_profile.name == "set_user_profile"
    assert get_user_profile_tool.name == "get_user_profile_tool"
    print("  store tools registered")


if __name__ == "__main__":
    tmp = _setup_tmp_db()
    try:
        tests = [
            test_save_and_get_profile,
            test_upsert_updates,
            test_build_context_empty,
            test_summarize_nutrition,
            test_tools_registered,
        ]
        passed = 0
        for t in tests:
            try:
                t()
                passed += 1
                print(f"  PASS: {t.__name__}")
            except Exception as e:
                print(f"  FAIL: {t.__name__} - {e}")
        print(f"\n{passed}/{len(tests)} tests passed")
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass