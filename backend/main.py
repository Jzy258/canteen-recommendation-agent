import asyncio
import json
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agent.agent import create_agent_executor
from agent.session import session_store
from middleware import (RequestMetricsMiddleware, add_tokens, get_metrics,
                        count_tokens, count_messages, clean_markdown,
                        StreamMarkdownCleaner, setup_logging, get_logger)
from version import APP_NAME, VERSION
from auth import auth_router, get_optional_user
from auth.admin import router as admin_router

# 统一日志系统（backend/logs，按天+大小滚动）
setup_logging()
logger = get_logger("canteen.app")

# 静态目录：本地 swagger-ui 资源（避免依赖 jsdelivr CDN）
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = FastAPI(title=APP_NAME, version=VERSION, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestMetricsMiddleware)

# 用户系统：认证接口（/auth/*）
app.include_router(auth_router)

# 管理员接口（/admin/*，require_admin 鉴权）
app.include_router(admin_router)

# 挂载本地 swagger-ui 静态资源
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# agent 改为按请求创建（绑定当前登录用户），见 chat / chat_stream

# ---- 推荐类工具输出 -> 前端结构化菜品/组合（建议1/2） ----
# 普通推荐/检索类工具：返回 list[dict] 或 dict（含 dishes）
_TOOL_DISH_LIST = {"recommend", "recommend_for_meal", "search_dish",
                   "get_all_dishes", "retrieve_dishes"}
# 组合优化工具：返回 dict（含 dishes + 汇总指标）
_TOOL_COMBO = {"optimize_meal_tool"}


def _pick_dish_fields(d: dict) -> dict:
    """从工具返回的菜品 dict 中提取前端展示所需字段（含 category）。"""
    return {
        "name": d.get("name", ""),
        "price": d.get("price", 0),
        "calories": d.get("calories"),
        "protein": d.get("protein"),
        "carbs": d.get("carbs"),
        "fat": d.get("fat"),
        "category": d.get("category", ""),
        "reason": d.get("reason") or "",
    }


def _normalize_tool_output(tool_name: str, output) -> dict | None:
    """把推荐/组合类工具的输出规范化为前端事件载荷。
    返回 {"dishes": [...]} 或 {"combo": {...}}；非相关工具返回 None。"""
    if output is None:
        return None
    if tool_name in _TOOL_COMBO:
        combo = dict(output)
        combo["dishes"] = [_pick_dish_fields(d) for d in (output.get("dishes") or [])]
        return {"combo": combo}
    if tool_name in _TOOL_DISH_LIST:
        if isinstance(output, dict) and "dishes" in output:
            dishes = output["dishes"]
        elif isinstance(output, dict):
            dishes = [output]
        elif isinstance(output, list):
            dishes = output
        else:
            return None
        return {"dishes": [_pick_dish_fields(d) for d in dishes]}
    return None

# 会话管理（线程安全 + TTL 过期 + 数量上限）由 SessionStore 承担


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
def custom_docs():
    """本地 Swagger UI（资源来自本地 static，不依赖 CDN）。"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{APP_NAME} - Swagger UI",
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        swagger_favicon_url="/static/swagger/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
def custom_redoc():
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{APP_NAME} - ReDoc",
    )


@app.get("/metrics")
def metrics():
    """查看中间件统计：请求数 / 耗时 / Token。"""
    return get_metrics()


@app.get("/trend")
def trend(days: int = 7, end_date: str = "",
          user: dict | None = Depends(get_optional_user)):
    """营养摄入趋势：连续 N 天每日营养合计（缺失日期补零），供前端趋势图。
    登录用户仅返回本人数据；游客返回全部。"""
    from db import get_db
    uid = user["id"] if user else None
    return get_db().get_weekly_trend(end_date=end_date, days=days, user_id=uid)


@app.get("/location")
def location(request: Request, lng: float | None = None, lat: float | None = None):
    """定位当前城市。
    1) 提供 lng/lat（浏览器定位坐标）→ 高德逆地理编码反查城市
    2) 否则按客户端 IP 定位（X-Forwarded-For / 直连 IP）
    失败返回 {"city": ""}。"""
    try:
        if lng is not None and lat is not None:
            return {"city": _reverse_geocode(lng, lat) or ""}
        from mcp.weather_data import auto_locate_city
        client_ip = _client_ip(request)
        return {"city": auto_locate_city(client_ip) or ""}
    except Exception:
        return {"city": ""}


@app.get("/dishes")
def dishes():
    """菜单页：返回全部菜品（含分类/价格/营养/口味标签）。"""
    from db import get_db
    return get_db().get_all_dishes()


def _reverse_geocode(lng: float, lat: float) -> str:
    """高德逆地理编码：坐标 → 城市名。返回空串表示失败。"""
    import json
    import urllib.request
    from urllib.parse import quote
    key = os.getenv("WEATHER_API_KEY", "")
    if not key:
        return ""
    url = (f"https://restapi.amap.com/v3/geocode/regeo"
           f"?key={key}&location={lng},{lat}&extensions=base&output=JSON")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "1":
            return ""
        ac = data.get("regeocode", {}).get("addressComponent", {})
        city = ac.get("city") or ac.get("province") or ""
        if isinstance(city, list):
            city = city[0] if city else ""
        return str(city).replace("市", "") if city else ""
    except Exception:
        return ""


def _client_ip(request: Request) -> str:
    """从请求提取客户端真实 IP（兼容 nginx 反代头）。
    若为内网/回环地址则返回空串，让定位接口用服务器出口 IP。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = ""
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            ip = first
    if not ip:
        ip = request.headers.get("x-real-ip", "") or ""
    if not ip and request.client:
        ip = request.client.host or ""
    # 内网/回环/本机地址：高德无法定位，交给接口用出口 IP
    if ip and _is_private_ip(ip):
        return ""
    return ip


def _is_private_ip(ip: str) -> bool:
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_unspecified


@app.get("/records")
def records(start_date: str = "", end_date: str = "", meal_time: str = "",
            user: dict | None = Depends(get_optional_user)):
    """历史饮食记录：默认最近 30 天，可按餐次过滤（breakfast/lunch/dinner/other）。
    登录用户仅返回本人记录；游客返回全部。"""
    from datetime import date, timedelta
    from db import get_db
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.fromisoformat(end_date) - timedelta(days=29)).isoformat()
    uid = user["id"] if user else None
    return get_db().get_records_in_range(start_date, end_date, meal_time,
                                         user_id=uid)


class RecordUpdateRequest(BaseModel):
    date: str | None = None
    meal_time: str | None = None
    dish_id: int | None = None
    portion: float | None = None
    grams: float | None = None


@app.put("/records/{record_id}")
def update_record(record_id: int, req: RecordUpdateRequest,
                  user: dict | None = Depends(get_optional_user)):
    """修改一条饮食记录（仅更新传入字段）。登录用户仅能改自己的。"""
    from db import get_db
    uid = user["id"] if user else None
    ok = get_db().update_meal_record(
        record_id,
        date=req.date,
        meal_time=req.meal_time,
        dish_id=req.dish_id,
        portion=req.portion,
        grams=req.grams,
        user_id=uid,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在或无权修改")
    return {"ok": True}


@app.delete("/records/{record_id}")
def delete_record(record_id: int, user: dict | None = Depends(get_optional_user)):
    """删除一条饮食记录。登录用户仅能删自己的。"""
    from db import get_db
    uid = user["id"] if user else None
    ok = get_db().delete_meal_record(record_id, user_id=uid)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在或无权删除")
    return {"ok": True}


class FoodRecordCreate(BaseModel):
    date: str
    meal_time: str
    name: str
    price: float = 0
    calories: float = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0
    grams: float = 0
    recommended_grams: float = 0
    remark: str = ""


class FoodRecordUpdate(BaseModel):
    date: str | None = None
    meal_time: str | None = None
    name: str | None = None
    price: float | None = None
    calories: float | None = None
    protein: float | None = None
    fat: float | None = None
    carbs: float | None = None
    grams: float | None = None
    recommended_grams: float | None = None
    remark: str | None = None


@app.get("/food-records")
def food_records(start_date: str = "", end_date: str = "", meal_time: str = "",
                 user: dict | None = Depends(get_optional_user)):
    """手工饮食记录列表（按日期倒序）。"""
    from db import get_db
    uid = user["id"] if user else None
    return get_db().get_food_records(
        start_date=start_date, end_date=end_date, meal_time=meal_time, user_id=uid)


@app.post("/food-records", status_code=201)
def create_food_record(req: FoodRecordCreate,
                       user: dict | None = Depends(get_optional_user)):
    """新增一条手工饮食记录。"""
    from db import get_db
    uid = user["id"] if user else None
    rid = get_db().add_food_record(
        date=req.date, meal_time=req.meal_time, name=req.name,
        price=req.price, calories=req.calories, protein=req.protein,
        fat=req.fat, carbs=req.carbs, grams=req.grams,
        recommended_grams=req.recommended_grams,
        remark=req.remark, user_id=uid)
    return {"id": rid, "ok": True}


@app.put("/food-records/{record_id}")
def update_food_record(record_id: int, req: FoodRecordUpdate,
                       user: dict | None = Depends(get_optional_user)):
    """修改一条手工饮食记录。"""
    from db import get_db
    uid = user["id"] if user else None
    ok = get_db().update_food_record(
        record_id, date=req.date, meal_time=req.meal_time, name=req.name,
        price=req.price, calories=req.calories, protein=req.protein,
        fat=req.fat, carbs=req.carbs, grams=req.grams,
        recommended_grams=req.recommended_grams,
        remark=req.remark, user_id=uid)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在或无权修改")
    return {"ok": True}


@app.delete("/food-records/{record_id}")
def delete_food_record(record_id: int, user: dict | None = Depends(get_optional_user)):
    """删除一条手工饮食记录。"""
    from db import get_db
    uid = user["id"] if user else None
    ok = get_db().delete_food_record(record_id, user_id=uid)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在或无权删除")
    return {"ok": True}


class CustomDishCreate(BaseModel):
    name: str
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    price: float = 0
    category: str = "自定义"
    serving_grams: float = 150


class CustomDishUpdate(BaseModel):
    name: str | None = None
    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    price: float | None = None
    category: str | None = None
    serving_grams: float | None = None


@app.get("/custom-dishes")
def list_custom_dishes(user: dict | None = Depends(get_optional_user)):
    """自定义菜品列表（登录用户仅本人；游客返回全部无主）。"""
    from db import get_db
    uid = user["id"] if user else None
    return get_db().list_custom_dishes(user_id=uid)


@app.post("/custom-dishes", status_code=201)
def create_custom_dish(req: CustomDishCreate,
                       user: dict | None = Depends(get_optional_user)):
    """新增自定义菜品（归属当前用户；游客存为无主）。"""
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="菜品名称不能为空")
    from db import get_db
    uid = user["id"] if user else None
    did = get_db().add_custom_dish(
        name=name, calories=req.calories or 0, protein=req.protein or 0,
        carbs=req.carbs or 0, fat=req.fat or 0, price=req.price or 0,
        category=req.category or "自定义",
        serving_grams=req.serving_grams or 150,
        user_id=uid)
    return {"id": did, "ok": True}


@app.put("/custom-dishes/{dish_id}")
def update_custom_dish(dish_id: int, req: CustomDishUpdate,
                       user: dict | None = Depends(get_optional_user)):
    """修改自定义菜品（仅更新传入字段；登录用户仅能改自己的或无主）。"""
    from db import get_db
    uid = user["id"] if user else None
    ok = get_db().update_custom_dish(
        dish_id, user_id=uid,
        name=req.name, calories=req.calories, protein=req.protein,
        carbs=req.carbs, fat=req.fat, price=req.price,
        category=req.category, serving_grams=req.serving_grams)
    if not ok:
        raise HTTPException(status_code=404, detail="菜品不存在或无权修改")
    return {"ok": True}


@app.delete("/custom-dishes/{dish_id}")
def delete_custom_dish(dish_id: int, user: dict | None = Depends(get_optional_user)):
    """删除自定义菜品（登录用户仅能删自己的或无主）。"""
    from db import get_db
    uid = user["id"] if user else None
    ok = get_db().delete_custom_dish(dish_id, user_id=uid)
    if not ok:
        raise HTTPException(status_code=404, detail="菜品不存在或无权删除")
    return {"ok": True}


class ProfileUpdateRequest(BaseModel):
    budget: float | None = None
    budget_min: float | None = None
    flavor_preferences: str | None = None
    dietary_restrictions: str | None = None
    health_goals: str | None = None
    region: str | None = None


@app.get("/profile")
def get_profile(user: dict | None = Depends(get_optional_user)):
    """获取当前用户偏好设置（登录用户按 user_id 隔离；游客返回全局/最近一条）。"""
    from db import get_db
    uid = user["id"] if user else None
    p = get_db().get_user_profile(user_id=uid) or {}
    return {
        "budget": p.get("budget", 20),
        "budget_min": p.get("budget_min", 0),
        "flavor_preferences": p.get("flavor_preferences", ""),
        "dietary_restrictions": p.get("dietary_restrictions", ""),
        "health_goals": p.get("health_goals", ""),
        "region": p.get("region", ""),
    }


@app.put("/profile")
def update_profile(req: ProfileUpdateRequest,
                   user: dict | None = Depends(get_optional_user)):
    """保存当前用户偏好设置（按 user_id 隔离；游客存为无主画像）。"""
    from db import get_db
    uid = user["id"] if user else None
    db = get_db()
    db.upsert_user_profile(
        budget=req.budget if req.budget is not None else 0,
        budget_min=req.budget_min if req.budget_min is not None else 0,
        flavor_preferences=req.flavor_preferences or "",
        dietary_restrictions=req.dietary_restrictions or "",
        health_goals=req.health_goals or "",
        region=req.region if req.region is not None else "",
        user_id=uid,
    )
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: dict | None = Depends(get_optional_user)):
    if not req.message or not req.message.strip():
        logger.warning("空消息被拒绝")
        raise HTTPException(status_code=400, detail="消息不能为空")

    uid = user["id"] if user else None
    session_id = req.session_id or str(uuid.uuid4())
    history = session_store.get(session_id)
    logger.info("chat 请求 | session=%s | msg=%s", session_id, req.message[:200])

    try:
        messages = history + [HumanMessage(content=req.message)]
        req_agent = create_agent_executor(uid)
        result = req_agent.invoke({"messages": messages})
        # last message is the final AI reply
        reply = clean_markdown(result["messages"][-1].content)
        # Token 统计（tiktoken 精确计数，回退字符估算）
        in_tokens = count_tokens(req.message) + count_messages(history)
        out_tokens = count_tokens(reply)
        add_tokens(in_tokens + out_tokens, user_id=uid)
        logger.info("chat 成功 | session=%s | in_tokens=%s out_tokens=%s | reply_len=%s",
                    session_id, in_tokens, out_tokens, len(reply))
    except Exception as e:
        logger.exception("chat 失败 | session=%s | msg=%s | err=%s",
                         session_id, req.message[:200], e)
        reply = "抱歉，系统处理出错，请稍后再试或换一种问法。"

    # persist to db (历史持久化)
    session_store.append(session_id, req.message, reply, user_id=uid)

    return ChatResponse(reply=reply, session_id=session_id)


def _stream_reply(session_id: str, message: str, user_id: int | None = None):
    """真实流式输出：通过 agent.astream_events 逐 token 推送 LLM 生成内容。"""
    history = session_store.get(session_id)
    logger.info("chat/stream 请求 | session=%s | msg=%s", session_id, message[:200])
    messages = history + [HumanMessage(content=message)]
    req_agent = create_agent_executor(user_id)

    async def gen():
        # 先发 session 元数据
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
        buffer = []
        errored = False
        cleaner = StreamMarkdownCleaner()
        # 收集工具返回的菜品结构化数据（推荐/检索），推给前端渲染菜品卡片。
        # 数据含完整营养信息，前端用它覆盖文本解析的卡片（文本里通常没有营养）。
        dish_data: list[dict] = []
        _seen_names: set[str] = set()
        # 过滤工具调用中间输出（避免前端看到 {"name":"recommend",...} 等 JSON）：
        # 工具调用的 AIMessageChunk 带 tool_call_chunks，其 content 属中间过程，
        # 实时丢弃；最终回复的 chunk 无 tool_call_chunks，正常实时推送。
        try:
            async for event in req_agent.astream_events(
                    {"messages": messages}, version="v2"):
                ev = event.get("event")
                if ev == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    # 工具调用 chunk：一律丢弃其 content，避免 JSON 泄露
                    if getattr(chunk, "tool_call_chunks", None):
                        continue
                    delta = chunk.content if isinstance(chunk.content, str) else ""
                    if delta:
                        # 逐增量清洗 Markdown，保证前端实时收到纯文本
                        clean_delta = cleaner.push(delta)
                        if clean_delta:
                            buffer.append(clean_delta)
                            payload = json.dumps({"type": "delta", "content": clean_delta},
                                                 ensure_ascii=False)
                            yield f"data: {payload}\n\n"
                elif ev == "on_tool_end":
                    # 捕获推荐/检索类工具返回的菜品数据
                    name = event.get("name", "")
                    out = event.get("data", {}).get("output")
                    if name in ("recommend_for_meal", "recommend", "retrieve_dishes"):
                        # on_tool_end 的 output 是 ToolMessage，content 为 JSON 字符串
                        parsed = None
                        if isinstance(out, dict):
                            parsed = out.get("dishes", out) if isinstance(out, (dict, list)) else None
                        elif hasattr(out, "content"):
                            content = out.content
                            if isinstance(content, str) and content.strip():
                                try:
                                    parsed = json.loads(content)
                                except Exception:
                                    parsed = None
                        items = []
                        if isinstance(parsed, dict):
                            items = parsed.get("dishes", []) if isinstance(parsed.get("dishes"), list) else []
                        elif isinstance(parsed, list):
                            items = parsed
                        for d in items:
                            if not isinstance(d, dict) or not d.get("name"):
                                continue
                            dn = d["name"]
                            if dn in _seen_names:
                                continue
                            _seen_names.add(dn)
                            dish_data.append({
                                "name": dn,
                                "price": d.get("price"),
                                "calories": d.get("calories"),
                                "protein": d.get("protein"),
                                "carbs": d.get("carbs"),
                                "fat": d.get("fat"),
                                "category": d.get("category"),
                                "reason": d.get("reason"),
                            })
                        if dish_data:
                            yield f"data: {json.dumps({'type': 'dishes', 'dishes': dish_data}, ensure_ascii=False)}\n\n"
                    elif name == "optimize_meal_tool":
                        # 组合优化工具：把结果作为 combo 事件下发（建议2：组合卡）
                        combo = None
                        if isinstance(out, dict):
                            combo = out
                        elif hasattr(out, "content") and isinstance(out.content, str) and out.content.strip():
                            try:
                                combo = json.loads(out.content)
                            except Exception:
                                combo = None
                        if isinstance(combo, dict) and combo.get("dishes"):
                            combo = dict(combo)
                            combo["dishes"] = [_pick_dish_fields(d) for d in combo["dishes"]
                                               if isinstance(d, dict)]
                            yield f"data: {json.dumps({'type': 'combo', 'combo': combo}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("chat/stream 失败 | session=%s | err=%s", session_id, e)
            errored = True

        # 兜底：若异常中断且无任何输出，清空流式 cleaner 残留作为回复
        reply = clean_markdown("".join(buffer) + cleaner.flush())
        if errored or not reply.strip():
            reply = "抱歉，系统处理出错，请稍后再试或换一种问法。"
            payload = json.dumps({"type": "delta", "content": reply},
                                 ensure_ascii=False)
            yield f"data: {payload}\n\n"

        # Token 统计 + 会话持久化（流式结束时统一处理）
        add_tokens(count_tokens(message) + count_tokens(reply), user_id=user_id)
        session_store.append(session_id, message, reply, user_id=user_id)
        logger.info("chat/stream 完成 | session=%s | reply_len=%s", session_id, len(reply))
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, user: dict | None = Depends(get_optional_user)):
    """流式对话：SSE 输出，先 session 元数据，再 content 增量，最后 done。"""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    session_id = req.session_id or str(uuid.uuid4())
    uid = user["id"] if user else None
    return _stream_reply(session_id, req.message, user_id=uid)


# =============================================================================
# 历史对话（v1.3）
# =============================================================================

@app.get("/sessions")
def list_sessions(user: dict | None = Depends(get_optional_user),
                  limit: int = 50):
    """历史会话列表（按更新时间倒序）。登录用户返回本人会话；游客返回全部。"""
    from db import get_db
    uid = user["id"] if user else None
    return get_db().list_chat_sessions(user_id=uid, limit=min(limit, 200))


@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str,
                         user: dict | None = Depends(get_optional_user)):
    """某会话的完整消息历史（供前端恢复对话）。
    登录用户仅能读本人的或历史无主（user_id NULL）会话；游客读任意。"""
    from db import get_db
    uid = user["id"] if user else None
    return get_db().get_chat_messages(session_id, user_id=uid)


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str,
                   user: dict | None = Depends(get_optional_user)):
    """删除历史会话（登录用户仅能删自己的；游客删任意）。"""
    from db import get_db
    uid = user["id"] if user else None
    ok = get_db().delete_chat_session(session_id, user_id=uid)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在或无权删除")
    return {"ok": True}


class SessionRenameRequest(BaseModel):
    title: str


@app.put("/sessions/{session_id}")
def rename_session(session_id: str, req: SessionRenameRequest,
                   user: dict | None = Depends(get_optional_user)):
    """重命名历史会话（登录用户仅能改自己的或无主会话；游客改任意）。"""
    from db import get_db
    uid = user["id"] if user else None
    title = (req.title or "").strip()[:50]
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    ok = get_db().rename_chat_session(session_id, title, user_id=uid)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在或无权修改")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
