"""生成测试用户与测试数据（B · v1.1.0 开发辅助）

用法：
    uv run python backend/scripts/seed_test_data.py

创建：
- 1 个管理员：admin / admin123
- 4 个普通用户：user1..user4（密码 test1234）
- 每用户一份 user_profile（预算/口味/健康目标）
- 每用户近 7 天若干已确认的饮食记录（含今天，供趋势图/记录页展示）
- 未来 7 天的每日三餐菜单（供推荐工具使用）

幂等：用户名已存在则跳过；记录/菜单追加不重复。
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import get_db
from auth.security import hash_password

# ---------- 测试用户 ----------
USERS = [
    {"username": "admin", "password": "admin123", "role": "admin", "display_name": "系统管理员",
     "profile": {"budget": 30, "flavor_preferences": "清淡,鲜", "health_goals": "控油"}},
    {"username": "user1", "password": "test1234", "role": "user", "display_name": "小张",
     "profile": {"budget": 20, "flavor_preferences": "辣", "health_goals": "高蛋白"}},
    {"username": "user2", "password": "test1234", "role": "user", "display_name": "小李",
     "profile": {"budget": 15, "flavor_preferences": "清淡", "health_goals": "减脂"}},
    {"username": "user3", "password": "test1234", "role": "user", "display_name": "小王",
     "profile": {"budget": 25, "flavor_preferences": "酸甜", "health_goals": "增肌"}},
    {"username": "user4", "password": "test1234", "role": "user", "display_name": "小赵",
     "profile": {"budget": 10, "flavor_preferences": "", "health_goals": "控糖"}},
]

MEALS = ["breakfast", "lunch", "dinner"]


def main():
    db = get_db()
    dishes = db.get_all_dishes()
    if not dishes:
        print("错误：菜品库为空，请先运行 data/init_db.py 导入菜品")
        sys.exit(1)
    dish_ids = [d["id"] for d in dishes]

    # 1) 创建用户 + 画像
    uid_map = {}
    for u in USERS:
        existing = db.get_user_by_username(u["username"])
        if existing is not None:
            print(f"[跳过] 用户 {u['username']} 已存在 (id={existing['id']})")
            uid_map[u["username"]] = existing["id"]
            continue
        uid = db.create_user(u["username"], hash_password(u["password"]),
                             role=u["role"], display_name=u["display_name"])
        uid_map[u["username"]] = uid
        p = u["profile"]
        db.upsert_user_profile(budget=p["budget"],
                               flavor_preferences=p["flavor_preferences"],
                               health_goals=p["health_goals"],
                               user_id=uid)
        print(f"[创建] 用户 {u['username']} (id={uid}, role={u['role']}) + 画像")

    # 2) 每用户近 7 天饮食记录（含今天），每天 2~3 餐已确认
    today = date.today()
    created_records = 0
    for uname, uid in uid_map.items():
        # 跳过 admin（无饮食记录，管理员不记饮食）
        if uname == "admin":
            continue
        for day_offset in range(7):
            d = today - timedelta(days=day_offset)
            dstr = d.isoformat()
            # 今天只记已过去的时间段（早餐/午餐必记，晚餐按概率）
            n_meals = len(MEALS)
            for meal in MEALS[:n_meals]:
                # 每餐 1~3 道菜
                import random
                random.seed(f"{uname}-{dstr}-{meal}")
                n_dishes = random.randint(1, 3)
                picks = random.sample(dish_ids, min(n_dishes, len(dish_ids)))
                for did in picks:
                    rid = db.add_meal_record(dstr, meal, did, portion=1.0, user_id=uid)
                    db.confirm_meal_record(rid)
                    created_records += 1
        print(f"[记录] {uname}: 近7天已确认记录已生成")

    # 3) 未来 7 天每日三餐菜单（覆盖式设置）
    created_menu = 0
    for day_offset in range(1, 8):
        d = (today + timedelta(days=day_offset)).isoformat()
        for meal in MEALS:
            import random
            random.seed(f"menu-{d}-{meal}")
            n = random.randint(3, 6)
            picks = random.sample(dish_ids, min(n, len(dish_ids)))
            db.add_menu_item(d, meal, picks)
            created_menu += 1
    print(f"[菜单] 未来 7 天 × 3 餐菜单已生成 ({created_menu} 条)")

    print(f"\n完成！共创建用户 {len(uid_map)} 个，饮食记录 {created_records} 条，菜单 {created_menu} 条")
    print("测试账号：admin/admin123, user1~user4/test1234")


if __name__ == "__main__":
    main()
