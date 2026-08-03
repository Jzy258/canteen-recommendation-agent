import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from mcp.weather_data import (
    get_weather,
    weather_to_dish_type,
    _mock_weather,
    city_to_adcode,
    _adcode_cache,
)
from mcp.weather_tool import get_weather_recommendation


def test_city_to_adcode():
    # 静态表命中
    assert city_to_adcode("北京") == "110000"
    print(f"  city_to_adcode 北京 = {city_to_adcode('北京')}")


def test_adcode_cache():
    # 动态解析后写入内存缓存，再次调用命中缓存不重复请求
    before = set(_adcode_cache.keys())
    ad = city_to_adcode("青岛")
    assert ad == "370200"
    assert "青岛" in _adcode_cache, "dynamic resolution should populate cache"
    # 缓存命中返回同一值
    assert city_to_adcode("青岛") == ad
    # 静态表不在 before 中，但应被加入（初始化时合并）
    print(f"  adcode cache: {len(_adcode_cache)} entries, 青岛={ad}")


def test_mock_weather_fields():
    d = _mock_weather("北京")
    for k in ["city", "temperature", "condition", "weather_type", "source"]:
        assert k in d, f"missing key {k}"
    assert d["source"] == "mock"
    print(f"  mock weather fields: {d['city']} {d['temperature']}°C {d['weather_type']}")


def test_get_weather_fields():
    # get_weather: real amap (if key set) or mock fallback — both must return full fields
    d = get_weather("北京")
    for k in ["city", "temperature", "condition", "weather_type", "source"]:
        assert k in d, f"missing key {k}"
    assert d["source"] in ("mock", "amap"), f"unknown source {d['source']}"
    print(f"  get_weather source={d['source']}: {d['temperature']}°C {d['weather_type']}")


def test_weather_type_valid():
    w = _mock_weather("北京")["weather_type"]
    assert w in ("cold", "hot", "mild"), f"invalid weather type {w}"
    print(f"  weather type valid: {w}")


def test_dish_direction_cold():
    assert "热汤" in weather_to_dish_type("cold")
    assert "面" in weather_to_dish_type("cold")
    print("  cold -> 热汤面类")


def test_dish_direction_hot():
    assert "清淡" in weather_to_dish_type("hot")
    print("  hot -> 清淡类")


def test_weather_recommendation_tool():
    r = get_weather_recommendation.invoke({"city": "广州"})
    assert isinstance(r, str) and r
    assert "°C" in r, "should include temperature"
    assert "推荐" in r or "建议" in r
    print(f"  recommendation: {r[:60]}...")


def test_weather_recommendation_cold_has_dishes():
    # force cold + mock mode: clear WEATHER_API_KEY and patch get_weather
    import os
    import mcp.weather_data as wd
    import mcp.weather_tool as wt
    import os
    import mcp.weather_tool as wt
    saved_key = os.getenv("WEATHER_API_KEY")
    os.environ["WEATHER_API_KEY"] = ""
    orig = wt.get_weather
    wt.get_weather = lambda city: {
        "city": city, "temperature": -5, "condition": "寒冷（mock 数据）",
        "weather_type": "cold", "source": "mock",
    }
    try:
        r = wt.get_weather_recommendation.invoke({"city": "北京"})
        assert "热汤" in r or "面" in r, f"cold should suggest warm dishes: {r}"
        print(f"  cold recommendation has dishes: OK")
    finally:
        wt.get_weather = orig
        if saved_key is None:
            os.environ.pop("WEATHER_API_KEY", None)
        else:
            os.environ["WEATHER_API_KEY"] = saved_key


if __name__ == "__main__":
    tests = [
        test_city_to_adcode,
        test_adcode_cache,
        test_mock_weather_fields,
        test_weather_type_valid,
        test_dish_direction_cold,
        test_dish_direction_hot,
        test_weather_recommendation_tool,
        test_weather_recommendation_cold_has_dishes,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} - {e}")
    print(f"\n{passed}/{len(tests)} tests passed")