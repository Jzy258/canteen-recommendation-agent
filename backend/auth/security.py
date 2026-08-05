"""用户系统 · 安全模块（A · v1.1）

- 密码哈希：标准库 PBKDF2-HMAC-SHA256（零第三方依赖）
- JWT 签发/校验：PyJWT
- JWT_SECRET 从 .env 读取；未配置时用随机值（进程重启后旧 Token 失效）
"""
import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

_ITERATIONS = 120_000
_ALGO = "sha256"

JWT_SECRET = os.getenv("JWT_SECRET", "") or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 默认 24h


# =============================================================================
# 密码哈希（PBKDF2-HMAC-SHA256，格式：pbkdf2$iterations$salt$hash）
# =============================================================================

def hash_password(password: str) -> str:
    """生成密码哈希。salt 随机 16 字节，迭代 12 万次。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        _ALGO, password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码与存储哈希是否匹配。格式不符返回 False。"""
    try:
        scheme, iters_s, salt_b64, digest_b64 = stored.split("$")
        if scheme != "pbkdf2":
            return False
        iterations = int(iters_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            _ALGO, password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# =============================================================================
# JWT
# =============================================================================

def create_access_token(user_id: int, username: str, role: str) -> str:
    """签发 JWT，payload 含 sub/username/role/exp/iat。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """校验 JWT。无效/过期返回 None。"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
