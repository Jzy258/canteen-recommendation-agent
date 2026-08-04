"""餐次判定（B 拥有 · 按当前时间自动决定推荐早/午/晚餐）

基于当前本地时间判断所属餐次：
- 早餐 breakfast：05:00-10:00
- 午餐 lunch：10:00-15:00
- 晚餐 dinner：15:00-22:00
- 深夜/凌晨 snack：22:00-05:00（提示夜宵建议）

可注入自定义时间便于测试（meal_time.now_override）。
"""
from datetime import datetime, time as dtime

# 餐次时间窗口（含起始，不含结束）
_MEAL_WINDOWS = {
    "breakfast": (dtime(5, 0), dtime(10, 0)),
    "lunch": (dtime(10, 0), dtime(15, 0)),
    "dinner": (dtime(15, 0), dtime(22, 0)),
}

MEAL_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "snack": "夜宵/加餐",
}

# 测试注入用
now_override: datetime | None = None


def _now() -> datetime:
    if now_override is not None:
        return now_override
    return datetime.now()


def current_meal() -> str:
    """返回当前餐次 key：breakfast / lunch / dinner / snack。"""
    t = _now().time()
    for meal, (start, end) in _MEAL_WINDOWS.items():
        if start <= t < end:
            return meal
    return "snack"


def current_meal_label() -> str:
    """返回当前餐次中文标签。"""
    return MEAL_LABELS[current_meal()]


def meal_label(meal: str) -> str:
    return MEAL_LABELS.get(meal, meal)