"""用户系统 · FastAPI 依赖注入（A · v1.1）

- get_current_user: 校验 Bearer Token，返回当前用户 dict（无效/未登录抛 401）
- require_admin: 在 get_current_user 基础上要求 role=admin
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import get_db
from auth.security import decode_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未登录或登录已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(creds: HTTPAuthorizationCredentials | None
                     = Depends(_bearer)) -> dict:
    """从 Authorization: Bearer <token> 解析并校验用户。"""
    if creds is None or not creds.credentials:
        raise _unauthorized()
    payload = decode_token(creds.credentials)
    if payload is None:
        raise _unauthorized()
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise _unauthorized()
    user = get_db().get_user_by_id(user_id)
    if user is None or user.get("status") != 1:
        raise _unauthorized()
    return user


def get_optional_user(creds: HTTPAuthorizationCredentials | None
                      = Depends(_bearer)) -> dict | None:
    """可选登录：带有效 Token 返回用户，否则返回 None（游客）。"""
    if creds is None or not creds.credentials:
        return None
    payload = decode_token(creds.credentials)
    if payload is None:
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    user = get_db().get_user_by_id(user_id)
    if user is None or user.get("status") != 1:
        return None
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """要求管理员角色。"""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
