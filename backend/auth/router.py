"""用户系统 · 认证路由（A · v1.1）

接口：
- POST /auth/register         注册（默认 user）
- POST /auth/login            登录，返回 JWT + 用户信息
- GET  /auth/me               当前用户信息
- POST /auth/change-password  修改密码（需旧密码）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from db import get_db
from auth.security import hash_password, verify_password, create_access_token
from auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user.get("display_name", ""),
    }


def _validate_password(password: str):
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")
    if len(password) > 128:
        raise HTTPException(status_code=400, detail="密码过长")


@router.post("/register")
def register(req: RegisterRequest):
    """注册新用户。username 唯一，默认角色 user。"""
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="请输入用户名")
    _validate_password(req.password)
    db = get_db()
    if db.get_user_by_username(username) is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")
    uid = db.create_user(username, hash_password(req.password),
                         role="user", display_name=req.display_name.strip())
    return {"id": uid, "username": username, "role": "user"}


@router.post("/login")
def login(req: LoginRequest):
    """登录校验，返回 access_token 与用户公开信息。"""
    user = get_db().get_user_by_username(req.username.strip())
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.get("status") != 1:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    get_db().update_user_login(user["id"])
    token = create_access_token(user["id"], user["username"], user["role"])
    return {"access_token": token, "token_type": "bearer",
            "user": _public_user(user)}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    """返回当前登录用户信息。"""
    return _public_user(user)


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """修改当前用户密码（需旧密码校验）。"""
    db = get_db()
    stored = user["password_hash"]
    if not verify_password(req.old_password, stored):
        raise HTTPException(status_code=400, detail="原密码不正确")
    _validate_password(req.new_password)
    db.change_user_password(user["id"], hash_password(req.new_password))
    return {"ok": True}
