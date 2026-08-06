"""生成完整的测试数据（项目完工验收/演示用）

用法：
    cd backend
    uv run python scripts/generate_test_data.py

生成内容（覆盖全部主体功能）：
- 4 个测试用户 user1~user4（密码 test1234）+ 用户画像（预算范围/口味/忌口/健康目标/城市）
- 每用户近 30 天饮食记录（food_record，含脂肪/碳水/实际克重/推荐克重/备注）
- 每用户多个自定义菜品（custom_dish）
- 每用户多个历史会话（chat_session/chat_message，含标题，聊天页可恢复）

幂等：用户已存在则跳过；记录/自定义菜按 (用户, 日期/名称) 去重补漏；
会话使用确定性 session_id（seed-<用户名>-<序号>），已存在则跳过。可重复运行。
"""
import os
import random
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import get_db
from db.db import DB_PATH
from auth.security import hash_password

# ---------------- 测试用户与画像 ----------------
USERS = [
    {
        "username": "user1", "password": "test1234", "role": "user", "display_name": "小张",
        "profile": {"budget": 20, "budget_min": 8, "flavor_preferences": "辣,重口",
                    "dietary_restrictions": "不吃香菜", "health_goals": "高蛋白", "region": "南京市"},
    },
    {
        "username": "user2", "password": "test1234", "role": "user", "display_name": "小丽",
        "profile": {"budget": 15, "budget_min": 6, "flavor_preferences": "清淡",
                    "dietary_restrictions": "", "health_goals": "减脂", "region": "南京市"},
    },
    {
        "username": "user3", "password": "test1234", "role": "user", "display_name": "小王",
        "profile": {"budget": 25, "budget_min": 10, "flavor_preferences": "酸甜,鲜",
                    "dietary_restrictions": "海鲜过敏", "health_goals": "增肌", "region": "上海市"},
    },
    {
        "username": "user4", "password": "test1234", "role": "user", "display_name": "小赵",
        "profile": {"budget": 10, "budget_min": 4, "flavor_preferences": "",
                    "dietary_restrictions": "", "health_goals": "控糖", "region": "北京市"},
    },
]

# ---------------- 自定义菜品（name, kcal, protein, carbs, fat, price, category, serving_grams） ----------------
CUSTOM_DISHES = {
    "user1": [
        ("妈妈牌红烧肉", 320, 24, 12, 22, 18, "荤菜", 180),
        ("外婆家番茄牛腩", 260, 20, 14, 15, 22, "荤菜", 200),
        ("自制冷面", 280, 9, 45, 8, 10, "主食", 300),
        ("低脂鸡胸沙拉", 180, 26, 10, 4, 15, "素菜", 200),
        ("蛋白粉燕麦杯", 250, 20, 30, 6, 12, "主食", 150),
    ],
    "user2": [
        ("清蒸鲈鱼", 150, 22, 3, 5, 25, "荤菜", 200),
        ("水煮西兰花", 45, 4, 8, 1, 8, "素菜", 150),
        ("杂粮饭", 160, 4, 30, 2, 3, "主食", 200),
        ("低糖酸奶杯", 90, 5, 12, 2, 6, "饮品", 150),
    ],
    "user3": [
        ("牛肉蛋炒饭", 380, 28, 45, 12, 16, "主食", 300),
        ("香煎三文鱼", 220, 25, 4, 12, 28, "荤菜", 180),
        ("高蛋白豆浆", 120, 10, 10, 4, 5, "饮品", 250),
        ("凉拌鸡丝", 160, 20, 6, 6, 12, "素菜", 150),
    ],
    "user4": [
        ("荞麦面", 220, 8, 40, 3, 9, "主食", 200),
        ("清炒时蔬", 60, 3, 10, 2, 6, "素菜", 150),
        ("无糖豆花", 80, 6, 6, 3, 5, "饮品", 200),
        ("蒸南瓜", 90, 2, 20, 1, 5, "主食", 180),
    ],
}

# ---------------- 历史会话（[(role, content), ...]，首个 user 消息作标题） ----------------
SESSIONS = {
    "user1": [
        [
            ("user", "今天中午吃什么好？预算20以内"),
            ("assistant", "您好！根据您的偏好（高蛋白、口味偏辣），推荐：辣子鸡丁、香辣牛肉饭、凉拌黄瓜。辣子鸡丁蛋白质丰富且符合口味，搭配凉拌黄瓜解腻，总价约18元，在预算内。需要我帮您记录吗？"),
            ("user", "好，记录辣子鸡丁"),
            ("assistant", "好的，已为您记录今天午餐的辣子鸡丁（推荐克重 150g）。还需要其他帮助吗？"),
            ("user", "不用了，谢谢"),
            ("assistant", "不客气！有需要随时找我～祝您用餐愉快！"),
        ],
        [
            ("user", "红烧肉的热量是多少？"),
            ("assistant", "红烧肉每份约 200 克，热量约 480 千卡，蛋白质 18 克，脂肪 40 克，碳水 15 克，价格约 22 元。属于荤菜，热量偏高，建议适量食用并搭配清淡蔬菜。"),
            ("user", "那有没有低脂的替代？"),
            ("assistant", "推荐您试试清蒸鱼或鸡胸肉：清蒸鱼约 150 千卡/份、蛋白质 22 克，脂肪仅 5 克；鸡胸肉约 180 千卡/份、蛋白质 26 克。都符合高蛋白低脂需求。"),
        ],
        [
            ("user", "明天南京天气怎么样？适合吃什么？"),
            ("assistant", "明天南京预计 28°C，多云，天气偏热。建议选择清淡解暑的菜品，比如凉拌木耳、清蒸鱼、绿豆汤，帮助消暑补水。"),
            ("user", "帮我推荐一份搭配"),
            ("assistant", "推荐：清蒸鲈鱼 + 凉拌木耳 + 杂粮饭，总价约 28 元，高蛋白低脂，适合炎热天气，营养均衡。"),
        ],
    ],
    "user2": [
        [
            ("user", "我在减脂，晚上吃什么好？"),
            ("assistant", "减脂期推荐清淡高纤维的组合：清蒸鲈鱼 + 水煮西兰花 + 杂粮饭。总热量约 350 千卡，蛋白质 30 克，脂肪低。晚餐这样吃既饱腹又不易长胖。"),
            ("user", "好的，记录一下清蒸鲈鱼"),
            ("assistant", "已为您记录今天晚餐的清蒸鲈鱼（推荐克重 200g）。减脂期记得搭配适量运动哦！"),
        ],
        [
            ("user", "早餐有什么推荐？"),
            ("assistant", "推荐：低糖酸奶杯 + 全麦面包 + 水煮蛋，热量约 380 千卡，蛋白质充足，适合减脂期早餐。"),
        ],
    ],
    "user3": [
        [
            ("user", "我要增肌，需要高蛋白餐，推荐一下"),
            ("assistant", "增肌推荐高蛋白高碳组合：牛肉蛋炒饭 + 香煎三文鱼 + 高蛋白豆浆。总热量约 720 千卡，蛋白质 63 克，搭配训练日食用效果更佳。"),
            ("user", "注意我对海鲜过敏"),
            ("assistant", "抱歉！已注意您对海鲜过敏，将三文鱼替换为鸡胸肉：牛肉蛋炒饭 + 香煎鸡胸 + 高蛋白豆浆，蛋白质同样充足且不含海鲜。"),
        ],
        [
            ("user", "上海今天天气怎么样，适合吃什么？"),
            ("assistant", "上海今天预计 24°C，小雨。雨天适合吃暖胃热食，推荐牛肉汤面或番茄牛腩，热汤暖身。"),
        ],
    ],
    "user4": [
        [
            ("user", "我在控糖，推荐一份午餐"),
            ("assistant", "控糖推荐低升糖组合：荞麦面 + 清炒时蔬 + 无糖豆花。总热量约 360 千卡，碳水约 56 克，升糖平缓，适合控糖人群。"),
            ("user", "荞麦面多少克合适？"),
            ("assistant", "建议荞麦面 150~200 克为宜，配合足量蔬菜，避免餐后血糖波动过大。"),
        ],
    ],
}

MEALS = ["breakfast", "lunch", "dinner"]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _exists_food(uid, dstr, meal, name):
    with _connect() as c:
        row = c.execute(
            "SELECT id FROM food_record WHERE user_id = ? AND date = ? AND meal_time = ? AND name = ?",
            (uid, dstr, meal, name)).fetchone()
        return row is not None


def _exists_custom(uid, name):
    with _connect() as c:
        row = c.execute(
            "SELECT id FROM custom_dish WHERE user_id = ? AND name = ?",
            (uid, name)).fetchone()
        return row is not None


def _exists_session(sid):
    with _connect() as c:
        row = c.execute(
            "SELECT id FROM chat_session WHERE session_id = ?", (sid,)).fetchone()
        return row is not None


def main():
    db = get_db()
    dishes = db.get_all_dishes()
    if not dishes:
        print("错误：菜品库为空，请先导入菜品（data/init_db.py）")
        sys.exit(1)
    by_id = {d["id"]: d for d in dishes}
    dish_ids = list(by_id.keys())
    today = date.today()

    stats = {"users": 0, "records": 0, "customs": 0, "sessions": 0, "messages": 0}

    for u in USERS:
        uname = u["username"]
        existing = db.get_user_by_username(uname)
        if existing is None:
            uid = db.create_user(uname, hash_password(u["password"]),
                                 role=u["role"], display_name=u["display_name"])
            p = u["profile"]
            db.upsert_user_profile(
                budget=p["budget"], budget_min=p["budget_min"],
                flavor_preferences=p["flavor_preferences"],
                dietary_restrictions=p["dietary_restrictions"],
                health_goals=p["health_goals"], region=p["region"], user_id=uid)
            stats["users"] += 1
            print(f"[用户] 创建 {uname} (id={uid}) + 画像")
        else:
            uid = existing["id"]
            print(f"[跳过] 用户 {uname} 已存在 (id={uid})")

        # ---- 1) 饮食记录：近 30 天，每天 1~3 餐，每餐 1~3 道菜 ----
        # 预生成确定性组合（随机决策一次性消耗），保证跨运行幂等：
        # 若在循环里"插入才消耗 random"，跳过/插入次数不同会导致序列偏移、重复生成。
        random.seed(f"rec-{uname}")
        combos = []
        for day_offset in range(30):
            dstr = (today - timedelta(days=day_offset)).isoformat()
            n_meals = random.randint(1, 3) if day_offset > 0 else random.randint(1, 2)
            for meal in random.sample(MEALS, n_meals):
                for did in random.sample(dish_ids, random.randint(1, 3)):
                    d = by_id[did]
                    rec = d.get("serving_grams") or 150
                    use_actual = random.random() < 0.7   # 是否说明实际克重
                    mult = random.uniform(0.6, 1.4)       # 实际克重系数
                    is_chat = random.random() < 0.3       # 是否来自聊天记录
                    combos.append((dstr, meal, d, rec, use_actual, mult, is_chat))
        for dstr, meal, d, rec, use_actual, mult, is_chat in combos:
            name = d["name"]
            if _exists_food(uid, dstr, meal, name):
                continue
            grams = round(rec * mult, 1) if use_actual else 0  # 0 = 未说明，用推荐克重
            remark = "（聊天记录）" if is_chat else ""
            db.add_food_record(
                date=dstr, meal_time=meal, name=name,
                price=d.get("price", 0), calories=d.get("calories", 0),
                protein=d.get("protein", 0), fat=d.get("fat", 0), carbs=d.get("carbs", 0),
                grams=grams, recommended_grams=rec, remark=remark, user_id=uid)
            stats["records"] += 1
        print(f"[记录] {uname}: 近30天饮食记录已生成/补漏")

        # ---- 2) 自定义菜品 ----
        for cd in CUSTOM_DISHES.get(uname, []):
            name, cal, pro, car, fat, price, cat, grams = cd
            if _exists_custom(uid, name):
                continue
            db.add_custom_dish(name=name, calories=cal, protein=pro, carbs=car,
                               fat=fat, price=price, category=cat, serving_grams=grams,
                               user_id=uid)
            stats["customs"] += 1
        print(f"[自定义菜] {uname}: 已生成/补漏")

        # ---- 3) 历史会话（确定性 session_id，幂等）----
        for i, turns in enumerate(SESSIONS.get(uname, [])):
            sid = f"seed-{uname}-{i + 1}"
            if _exists_session(sid):
                continue
            title = turns[0][1][:50] if turns and turns[0][1] else f"{uname}的测试会话"
            for role, content in turns:
                db.add_chat_message(sid, role, content, user_id=uid)
                stats["messages"] += 1
            db.rename_chat_session(sid, title, user_id=uid)
            stats["sessions"] += 1
        print(f"[会话] {uname}: 已生成/补漏")

    print("\n完成！本次新增："
          f"用户 {stats['users']} · 饮食记录 {stats['records']} · "
          f"自定义菜 {stats['customs']} · 会话 {stats['sessions']} · 消息 {stats['messages']}")
    print("测试账号：user1~user4 / test1234（admin / admin123）")


if __name__ == "__main__":
    main()
