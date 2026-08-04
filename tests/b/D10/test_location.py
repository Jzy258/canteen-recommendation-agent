import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

import mcp.location as loc
from mcp.location import locate_city, clear_cache
from mcp.weather_data import auto_locate_city, get_weather


def test_locate_override():
    loc.loc_override = {"city": "上海", "adcode": "310000", "province": "上海市"}
    try:
        info = locate_city()
        assert info["city"] == "上海"
        assert info["adcode"] == "310000"
    finally:
        loc.loc_override = None
    print("  locate_override: 上海/310000")


def test_locate_empty_without_key():
    # 无 key 时应返回空 dict 而非异常
    loc.loc_override = None
    import os
    saved = os.getenv("WEATHER_API_KEY")
    os.environ["WEATHER_API_KEY"] = ""
    try:
        info = locate_city("114.247.50.2")
        assert info == {}, "no key -> empty dict"
    finally:
        if saved is None:
            os.environ.pop("WEATHER_API_KEY", None)
        else:
            os.environ["WEATHER_API_KEY"] = saved
    print("  no-key returns empty dict")


def test_auto_locate_city_override():
    # 通过注入定位信息，验证 auto_locate_city 拿到城市名
    loc.loc_override = {"city": "广州", "adcode": "440100", "province": "广东省"}
    try:
        city = auto_locate_city()
        assert city == "广州"
    finally:
        loc.loc_override = None
    print("  auto_locate_city -> 广州")


def test_weather_without_city_falls_back():
    # 不传 city 且无法定位时，回退北京不报错
    loc.loc_override = None
    import os
    saved = os.getenv("WEATHER_API_KEY")
    os.environ["WEATHER_API_KEY"] = ""
    try:
        w = get_weather("")
        assert w["city"] in ("北京", ""), f"fallback city: {w['city']}"
        assert "temperature" in w
    finally:
        if saved is None:
            os.environ.pop("WEATHER_API_KEY", None)
        else:
            os.environ["WEATHER_API_KEY"] = saved
    print("  weather fallback without city OK")


def test_weather_tool_accepts_empty_city():
    # 工具接口 city 留空可调用
    import os
    from mcp.weather_tool import get_weather_recommendation
    saved = os.getenv("WEATHER_API_KEY")
    os.environ["WEATHER_API_KEY"] = ""
    try:
        r = get_weather_recommendation.invoke({"city": ""})
        assert isinstance(r, str) and r
    finally:
        if saved is None:
            os.environ.pop("WEATHER_API_KEY", None)
        else:
            os.environ["WEATHER_API_KEY"] = saved
    print("  weather tool empty city OK")


def test_location_module_path():
    # 定位缓存路径应解析到 backend/data
    assert "backend" in str(loc._LOC_CACHE_FILE).replace("\\", "/")
    print(f"  loc cache file: {loc._LOC_CACHE_FILE}")


if __name__ == "__main__":
    tests = [
        test_locate_override,
        test_locate_empty_without_key,
        test_auto_locate_city_override,
        test_weather_without_city_falls_back,
        test_weather_tool_accepts_empty_city,
        test_location_module_path,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except Exception as e:
            print(f"  FAIL: {t.__name__} - {e}")
    clear_cache()
    print(f"\n{passed}/{len(tests)} tests passed")