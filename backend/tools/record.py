from datetime import date, timedelta

from langchain_core.tools import tool


def _db():
    from db import get_db
    return get_db()


def _normalize_date(date_str: str) -> str:
    """将相对日期（today/今天/yesterday/昨天/前天/明天）规范化为真实 ISO 日期。

    防止 LLM 把"今天/昨天"直接当作 date 传入（如 date='today'），
    否则该记录无法被按日期范围的查询命中，导致记录页看不到。
    """
    s = (date_str or "").strip().lower()
    today = date.today()
    mapping = {
        "today": today,
        "今天": today,
        "今日": today,
        "yesterday": today - timedelta(days=1),
        "昨天": today - timedelta(days=1),
        "前天": today - timedelta(days=2),
        "tomorrow": today + timedelta(days=1),
        "明天": today + timedelta(days=1),
    }
    return mapping[s].isoformat() if s in mapping else date_str


def make_record_meal(user_id: int | None = None):
    """构造 record_meal 工具并闭包绑定归属用户（agent 运行时按当前登录用户注入）。"""
    @tool
    def record_meal(date: str, meal_time: str, dish_id: int, portion: float = 1.0,
                    grams: float | None = None) -> int:
        """记录一餐摄入（待确认状态），返回记录 id。
        date：日期（YYYY-MM-DD），也支持 today/今天/昨天 等相对写法。
        grams：实际摄入克重（可选）。提供时按克重折算营养；不提供则按 portion 份数。"""
        db = _db()
        n_date = _normalize_date(date)
        rid = db.add_meal_record(n_date, meal_time, dish_id, portion,
                                 user_id=user_id, grams=grams)
        # 同步写入 food_record（饮食记录页数据源），确保聊天记录的饮食在记录页可见。
        # 写 food_record 失败不影响主流程（meal_record 仍用于趋势/营养统计）。
        try:
            dish = db.get_dish_by_id(dish_id)
            if dish:
                db.add_food_record(
                    date=n_date,
                    meal_time=meal_time,
                    name=dish.get("name") or "",
                    price=dish.get("price") or 0,
                    calories=dish.get("calories") or 0,
                    protein=dish.get("protein") or 0,
                    fat=dish.get("fat") or 0,
                    carbs=dish.get("carbs") or 0,
                    grams=grams or 0,
                    recommended_grams=dish.get("serving_grams") or 0,
                    remark="（聊天记录）",
                    user_id=user_id,
                )
        except Exception:
            pass
        return rid
    return record_meal


# 默认（游客）record_meal，供工具注册中心引用
record_meal = make_record_meal(None)


@tool
def confirm_record(record_id: int) -> bool:
    """确认一条待审批的摄入记录。"""
    return _db().confirm_meal_record(record_id)


@tool
def reject_record(record_id: int) -> bool:
    """拒绝一条待审批的摄入记录。"""
    return _db().reject_meal_record(record_id)


@tool
def get_pending_records() -> list[dict]:
    """获取全部待审批（HITL）的摄入记录。"""
    return _db().get_pending_records()


@tool
def get_pending_records_by_date(date: str, meal_time: str = "") -> list[dict]:
    """按日期（可选餐次）获取待审批摄入记录。"""
    return _db().get_pending_records_by_date(date=date, meal_time=meal_time)


@tool
def get_pending_record(record_id: int) -> dict:
    """按 id 查询单条待审批记录。"""
    return _db().get_pending_record(record_id)


@tool
def confirm_records(record_ids: list[int]) -> int:
    """批量确认多条待审批记录，返回实际确认条数。"""
    return _db().confirm_records(record_ids)


@tool
def reject_records(record_ids: list[int]) -> int:
    """批量拒绝多条待审批记录，返回实际拒绝条数。"""
    return _db().reject_records(record_ids)


@tool
def get_daily_intake(date: str) -> list[dict]:
    """获取某日按餐次拆分的营养摄入。"""
    return _db().get_daily_nutrition(date)


@tool
def get_day_total(date: str) -> dict:
    """获取某日全天营养合计。"""
    return _db().get_day_total(date)


@tool
def get_weekly_trend(end_date: str = "", days: int = 7) -> list[dict]:
    """获取最近 N 天每日营养合计（缺失日期补零，供趋势图）。"""
    return _db().get_weekly_trend(end_date=end_date, days=days)


@tool
def get_weekly_summary(start_date: str = "", end_date: str = "") -> dict:
    """获取周营养汇总（合计 + 天数 + 菜品数）。"""
    return _db().get_weekly_summary(start_date=start_date, end_date=end_date)