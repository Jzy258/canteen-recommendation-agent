"""用户系统 · 管理员接口（B · v1.1 D8c）

接口（统一前缀 /admin，全部 require_admin）：
- GET    /admin/stats          全局统计概览
- GET    /admin/users          用户列表（分页 + 搜索）
- PATCH  /admin/users/{id}     修改用户（角色/启用禁用/昵称）
- POST   /admin/users/{id}/reset-password  重置密码
- GET    /admin/dishes         菜品列表
- POST   /admin/dishes         新增菜品
- PATCH  /admin/dishes/{id}    更新菜品
- DELETE /admin/dishes/{id}    删除菜品
- PUT    /admin/menu           设置某日期餐次菜单（覆盖式）
- DELETE /admin/menu           删除某日期餐次菜单
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import get_db
from auth.deps import require_admin
from auth.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user.get("display_name", ""),
        "status": user.get("status", 1),
        "created_at": user.get("created_at", ""),
        "last_login_at": user.get("last_login_at"),
    }


# ===================== 统计 =====================


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats():
    """全局运营统计：用户/菜品/菜单/摄入记录数。"""
    return get_db().get_global_stats()


# ===================== 用户管理 =====================


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(keyword: str = "", limit: int = Query(50, ge=1, le=200),
               offset: int = Query(0, ge=0)):
    """用户列表（分页 + username/昵称模糊搜索）。"""
    rows = get_db().list_users(keyword=keyword, limit=limit, offset=offset)
    return {"items": [_public_user(u) for u in rows], "count": len(rows)}


class UserUpdateRequest(BaseModel):
    role: str | None = Field(None, pattern="^(admin|user)$")
    status: int | None = Field(None, ge=0, le=1)
    display_name: str | None = None


@router.patch("/users/{user_id}", dependencies=[Depends(require_admin)])
def update_user(user_id: int, req: UserUpdateRequest,
                me: dict = Depends(require_admin)):
    """修改用户：角色 / 启用禁用 / 昵称。"""
    db = get_db()
    user = db.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    is_self = user_id == me["id"]
    if req.role is not None and req.role != user["role"]:
        if is_self:
            raise HTTPException(status_code=400, detail="不能修改自己的角色")
        db.set_user_role(user_id, req.role)
    if req.status is not None and req.status != user["status"]:
        if is_self:
            raise HTTPException(status_code=400, detail="不能禁用自己的账号")
        db.set_user_status(user_id, req.status)
    if req.display_name is not None and req.display_name.strip() != user.get("display_name"):
        db.set_user_display_name(user_id, req.display_name.strip())
    return {"ok": True}


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


@router.post("/users/{user_id}/reset-password",
             dependencies=[Depends(require_admin)])
def reset_password(user_id: int, req: ResetPasswordRequest):
    """管理员重置任意用户密码。"""
    db = get_db()
    if db.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.change_user_password(user_id, hash_password(req.new_password))
    return {"ok": True}


# ===================== Token 用量 =====================


@router.get("/feedback", dependencies=[Depends(require_admin)])
def list_feedback(keyword: str = "", limit: int = Query(100, ge=1, le=200),
                  offset: int = Query(0, ge=0)):
    """反馈列表（分页 + 内容/联系方式搜索）。"""
    rows = get_db().list_feedback(keyword=keyword, limit=limit, offset=offset)
    return {"items": rows, "count": len(rows)}


@router.delete("/feedback/{feedback_id}", dependencies=[Depends(require_admin)])
def delete_feedback(feedback_id: int):
    """删除一条反馈。"""
    if not get_db().delete_feedback(feedback_id):
        raise HTTPException(status_code=404, detail="反馈不存在")
    return {"ok": True}


@router.get("/token-usage", dependencies=[Depends(require_admin)])
def token_usage():
    """每个用户的 Token 用量（按 user_id 累计，不随进程重启清零；0 用量的用户也列出）。"""
    from middleware.metrics import get_token_usage_by_user
    by_user = get_token_usage_by_user()
    rows = get_db().list_users(limit=200, offset=0)
    items = []
    for u in rows:
        items.append({
            "id": u["id"],
            "username": u["username"],
            "display_name": u.get("display_name", ""),
            "role": u.get("role", "user"),
            "status": u.get("status", 1),
            "tokens": int(by_user.get(str(u["id"]), 0)),
        })
    items.sort(key=lambda x: x["tokens"], reverse=True)
    total = sum(i["tokens"] for i in items)
    return {"items": items, "total_tokens": total}


# ===================== 菜品管理 =====================


class DishCreateRequest(BaseModel):
    name: str
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    price: float = 0
    category: str = ""
    flavor_tags: str = ""
    source: str = ""


class DishUpdateRequest(BaseModel):
    name: str | None = None
    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    price: float | None = None
    category: str | None = None
    flavor_tags: str | None = None
    source: str | None = None


@router.get("/dishes", dependencies=[Depends(require_admin)])
def list_dishes(keyword: str = "", category: str = "",
                limit: int = Query(100, ge=1, le=500),
                offset: int = Query(0, ge=0)):
    """菜品列表（分页 + 名称/类别过滤）。"""
    db = get_db()
    rows = db.get_all_dishes()
    if keyword:
        rows = [d for d in rows if keyword in d["name"]]
    if category:
        rows = [d for d in rows if d.get("category") == category]
    items = rows[offset:offset + limit]
    return {"items": items, "total": len(rows), "count": len(items)}


@router.post("/dishes", status_code=201, dependencies=[Depends(require_admin)])
def create_dish(req: DishCreateRequest):
    """新增菜品。"""
    db = get_db()
    if db.get_dish_by_name(req.name.strip()):
        raise HTTPException(status_code=409, detail="菜品名称已存在")
    try:
        dish_id = db.add_dish(req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建菜品失败: {e}")
    return {"id": dish_id}


@router.patch("/dishes/{dish_id}", dependencies=[Depends(require_admin)])
def update_dish(dish_id: int, req: DishUpdateRequest):
    """更新菜品（仅更新传入字段）。"""
    db = get_db()
    if db.get_dish_by_id(dish_id) is None:
        raise HTTPException(status_code=404, detail="菜品不存在")
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        db.update_dish(dish_id, data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新菜品失败: {e}")
    return {"ok": True}


@router.delete("/dishes/{dish_id}", dependencies=[Depends(require_admin)])
def delete_dish(dish_id: int):
    """删除菜品（关联 menu_item 级联删除）。"""
    db = get_db()
    if db.get_dish_by_id(dish_id) is None:
        raise HTTPException(status_code=404, detail="菜品不存在")
    db.delete_dish(dish_id)
    return {"ok": True}


# ===================== 菜单管理 =====================


class MenuRequest(BaseModel):
    date: str
    meal_time: str
    dish_ids: list[int] = Field(default_factory=list)


@router.get("/menu", dependencies=[Depends(require_admin)])
def get_menu(date: str, meal_time: str):
    """查询某日期餐次的菜单菜品列表（供后台菜单管理回显）。"""
    return get_db().get_dishes_for_menu(date, meal_time)


@router.put("/menu", dependencies=[Depends(require_admin)])
def set_menu(req: MenuRequest):
    """设置某日期餐次的菜单（覆盖式重设菜品关联）。"""
    db = get_db()
    result = db.add_menu_item(req.date, req.meal_time, req.dish_ids)
    return {"ok": True, **result}


@router.delete("/menu", dependencies=[Depends(require_admin)])
def delete_menu(date: str, meal_time: str):
    """删除某日期餐次的菜单。"""
    db = get_db()
    if not db.delete_menu(date, meal_time):
        raise HTTPException(status_code=404, detail="菜单不存在")
    return {"ok": True}
