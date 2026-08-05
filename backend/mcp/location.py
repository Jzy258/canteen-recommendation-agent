"""市级定位（B 拥有 · 高德 IP 定位）

通过高德 IP 定位接口，将用户 IP 解析为所在城市与 adcode，
供天气查询工具自动定位城市（用户不传 city 时）。

接口：https://lbs.amap.com/api/webservice/guide/api/ipconfig
  GET {IP_BASE_URL}?key={key}&ip={ip}&output=JSON
  - ip 不传则取请求来源 IP
  - 返回 province / city / adcode

定位结果缓存（内存 + 文件），避免频繁请求。
"""
import json
import os
import threading
import urllib.request
from urllib.parse import quote

from dotenv import load_dotenv

# .env 位于 backend/.env（mcp/location.py -> 上一级是 backend）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# 定位缓存文件
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOC_CACHE_FILE = os.getenv("LOC_CACHE_FILE",
                            os.path.join(_BACKEND_DIR, "data", "loc_cache.json"))
_loc_cache: dict[str, dict] = {}
_loc_lock = threading.Lock()

# 测试注入用
loc_override: dict | None = None


def _load_cache() -> dict[str, dict]:
    try:
        if os.path.exists(_LOC_CACHE_FILE):
            with open(_LOC_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_cache():
    try:
        os.makedirs(os.path.dirname(_LOC_CACHE_FILE), exist_ok=True)
        with open(_LOC_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_loc_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_loc_cache = _load_cache()


def locate_city(ip: str = "") -> dict:
    """根据 IP 定位城市。返回 {city, adcode, province}。
    - ip 为空时使用请求来源 IP
    - 失败/未配置 key 时返回空 dict（调用方回退默认城市）
    """
    if loc_override is not None:
        return dict(loc_override)

    key = os.getenv("WEATHER_API_KEY", "")
    if not key:
        return {}

    cache_key = ip or "default"
    with _loc_lock:
        if cache_key in _loc_cache:
            return dict(_loc_cache[cache_key])

    base = os.getenv("IP_BASE_URL", "https://restapi.amap.com/v3/ip")
    url = f"{base}?key={key}&output=JSON"
    if ip:
        url += f"&ip={quote(ip)}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "1":
            return {}
        city = data.get("city") or data.get("province") or ""
        adcode = data.get("adcode") or ""
        if not city:
            return {}
        result = {
            "city": city,
            "adcode": adcode,
            "province": data.get("province", ""),
        }
        with _loc_lock:
            _loc_cache[cache_key] = result
        _save_cache()
        return result
    except Exception:
        return {}


def clear_cache():
    """清空定位缓存（测试用）。"""
    with _loc_lock:
        _loc_cache.clear()
    try:
        if os.path.exists(_LOC_CACHE_FILE):
            os.remove(_LOC_CACHE_FILE)
    except Exception:
        pass