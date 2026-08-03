"""天气数据源与推荐方向（B 拥有 · D6）

纯逻辑模块，不依赖 MCP SDK，供 weather_server（MCP 进程）与
weather_tool（Agent 侧）共用。

数据源双模式：
- 真实 API（高德）：配置 WEATHER_API_KEY + WEATHER_BASE_URL 时启用。
  地理编码查 adcode：https://lbs.amap.com/api/webservice/guide/api/georegeo
    GET {GEOCODE_BASE_URL}?key={key}&address={城市}&output=JSON
  天气查询：https://lbs.amap.com/api/webservice/guide/api/weatherinfo
    GET {WEATHER_BASE_URL}?key={key}&city={adcode}&extensions=base&output=JSON
- mock 回退：未配置或调用失败时使用本地季节温度表。
"""
import json
import os
import random
import threading
import urllib.request
from datetime import datetime
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

# 城市名 → 高德 adcode 兜底映射（优先用地理编码接口动态解析）
CITY_ADCODE = {
    "北京": "110000",
    "上海": "310000",
    "广州": "440100",
    "深圳": "440300",
    "成都": "510100",
    "西安": "610100",
    "武汉": "420100",
    "杭州": "330100",
    "南京": "320100",
    "重庆": "500000",
}

# adcode 缓存：内存 dict + 持久化 JSON 文件（避免每次查询都调地理编码接口）
_ADCODE_CACHE_FILE = os.getenv("ADCODE_CACHE_FILE", "backend/data/adcode_cache.json")
_adcode_cache: dict[str, str] = {}
_cache_lock = threading.Lock()


def _load_adcode_cache() -> dict[str, str]:
    """进程启动时加载持久化缓存（合并静态表）。"""
    cache = dict(CITY_ADCODE)
    try:
        if os.path.exists(_ADCODE_CACHE_FILE):
            with open(_ADCODE_CACHE_FILE, encoding="utf-8") as f:
                stored = json.load(f)
            cache.update(stored)
    except Exception:
        pass
    return cache


def _save_adcode_cache():
    """将内存缓存落盘（含静态表 + 动态解析结果）。"""
    try:
        os.makedirs(os.path.dirname(_ADCODE_CACHE_FILE), exist_ok=True)
        with open(_ADCODE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_adcode_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# 初始化内存缓存
_adcode_cache = _load_adcode_cache()

_MOCK_CITIES = {
    "北京": {"winter": -3, "spring": 16, "summer": 30, "autumn": 15},
    "上海": {"winter": 5, "spring": 18, "summer": 31, "autumn": 19},
    "广州": {"winter": 14, "spring": 22, "summer": 32, "autumn": 24},
    "深圳": {"winter": 15, "spring": 23, "summer": 32, "autumn": 25},
    "成都": {"winter": 6, "spring": 17, "summer": 28, "autumn": 17},
    "西安": {"winter": -1, "spring": 15, "summer": 29, "autumn": 14},
    "武汉": {"winter": 4, "spring": 18, "summer": 32, "autumn": 19},
    "杭州": {"winter": 4, "spring": 17, "summer": 31, "autumn": 18},
    "南京": {"winter": 3, "spring": 16, "summer": 30, "autumn": 18},
    "重庆": {"winter": 7, "spring": 19, "summer": 33, "autumn": 19},
}


def _season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def get_weather(city: str = "北京") -> dict:
    """获取城市温度与天气类型。优先真实 API，失败回退 mock。"""
    if os.getenv("WEATHER_API_KEY"):
        try:
            return _real_weather(city)
        except Exception as e:
            # 真实 API 失败降级 mock，保证链路可用
            result = _mock_weather(city)
            result["note"] = f"real api failed: {e}, fallback to mock"
            return result
    return _mock_weather(city)


def city_to_adcode(city: str) -> str:
    """地理编码接口动态解析城市名 → adcode，带内存 + 文件缓存。

    命中缓存直接返回（静态表 + 历史解析结果），未命中才调地理编码接口：
    GET {GEOCODE_BASE_URL}?key={key}&address={城市}&output=JSON
    返回 geocodes[0].adcode。
    """
    with _cache_lock:
        if city in _adcode_cache:
            return _adcode_cache[city]

    base = os.getenv("GEOCODE_BASE_URL", "https://restapi.amap.com/v3/geocode/geo")
    key = os.getenv("WEATHER_API_KEY", "")
    url = f"{base}?key={key}&address={quote(city)}&output=JSON"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("status") != "1" or not data.get("geocodes"):
        raise RuntimeError(f"geocode status={data.get('status')} info={data.get('info')}")
    adcode = data["geocodes"][0].get("adcode")
    if not adcode:
        raise RuntimeError(f"geocode no adcode for {city}")

    # 写入缓存并落盘
    with _cache_lock:
        _adcode_cache[city] = adcode
    _save_adcode_cache()
    return adcode


def _real_weather(city: str) -> dict:
    """高德天气 API：GET {WEATHER_BASE_URL}?key=&city=&extensions=base&output=JSON

    city 参数需要 adcode（城市编码），先经地理编码接口动态解析，失败回退静态表。
    返回实况天气 lives[0]：temperature（℃）、weather（天气现象汉字）。
    """
    base = os.getenv("WEATHER_BASE_URL",
                     "https://restapi.amap.com/v3/weather/weatherInfo")
    key = os.getenv("WEATHER_API_KEY", "")
    try:
        adcode = city_to_adcode(city)
    except Exception:
        adcode = CITY_ADCODE.get(city, CITY_ADCODE["北京"])

    url = (f"{base}?key={key}&city={adcode}&extensions=base&output=JSON")
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("status") != "1" or not data.get("lives"):
        raise RuntimeError(f"amap status={data.get('status')} info={data.get('info')}")

    live = data["lives"][0]
    temp = float(live["temperature"])
    weather_desc = live.get("weather", "")
    weather_type = "cold" if temp <= 10 else ("hot" if temp >= 28 else "mild")
    desc = ("寒冷" if weather_type == "cold"
            else "炎热" if weather_type == "hot" else "温和")

    return {
        "city": live.get("city", city),
        "temperature": temp,
        "condition": f"{weather_desc}（{desc}）",
        "weather_type": weather_type,
        "source": "amap",
        "report_time": live.get("reporttime", ""),
    }


def _mock_weather(city: str) -> dict:
    season = _season(datetime.now().month)
    base = _MOCK_CITIES.get(city, _MOCK_CITIES["北京"])[season]
    temp = base + random.randint(-2, 2)
    weather_type = "cold" if temp <= 10 else ("hot" if temp >= 28 else "mild")
    desc = ("寒冷" if weather_type == "cold"
            else "炎热" if weather_type == "hot" else "温和")
    return {
        "city": city,
        "temperature": temp,
        "condition": f"{desc}（mock 数据）",
        "weather_type": weather_type,
        "source": "mock",
    }


def weather_to_dish_type(weather_type: str) -> str:
    """天气类型 → 推荐菜品方向（冷→热汤面，热→清淡）。"""
    if weather_type == "cold":
        return "热汤面类（热汤、炖菜、面食）"
    if weather_type == "hot":
        return "清淡类（凉菜、清蒸、水果）"
    return "常规均衡搭配"