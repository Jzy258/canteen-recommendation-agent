"""创建初始管理员账号（A · v1.1）

用法：
    uv run python backend/scripts/create_admin.py --username admin --password secret123
    uv run python backend/scripts/create_admin.py --username admin   # 密码从 ADMIN_INIT_PASSWORD env 或交互输入

密码来源优先级：--password 参数 > ADMIN_INIT_PASSWORD 环境变量 > 交互输入。
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import get_db
from auth.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="创建管理员账号")
    parser.add_argument("--username", default="admin", help="管理员用户名")
    parser.add_argument("--password", default="", help="管理员密码（不传则用 ADMIN_INIT_PASSWORD 或交互输入）")
    parser.add_argument("--display-name", default="", help="昵称")
    args = parser.parse_args()

    username = args.username.strip()
    password = args.password or os.getenv("ADMIN_INIT_PASSWORD", "")
    if not password:
        password = getpass.getpass(f"请输入 {username} 的密码（至少6位）: ")
    if len(password) < 6:
        print("错误：密码至少 6 位", file=sys.stderr)
        sys.exit(1)

    db = get_db()
    existing = db.get_user_by_username(username)
    if existing is not None:
        print(f"用户 {username} 已存在 (id={existing['id']}, role={existing['role']})，跳过创建")
        sys.exit(0)

    uid = db.create_user(username, hash_password(password),
                         role="admin", display_name=args.display_name.strip())
    print(f"管理员创建成功: id={uid}, username={username}, role=admin")


if __name__ == "__main__":
    main()
