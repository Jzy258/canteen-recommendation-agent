import asyncio
import json
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
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

agent = create_agent_executor()

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
def location():
    """通过 IP 定位当前所在城市（供前端定位；本地/内网 IP 可能定位失败）。"""
    try:
        from mcp.weather_data import auto_locate_city
        return {"city": auto_locate_city() or ""}
    except Exception:
        return {"city": ""}


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


class ProfileUpdateRequest(BaseModel):
    budget: float | None = None
    flavor_preferences: str | None = None
    health_goals: str | None = None


@app.get("/profile")
def get_profile(user: dict | None = Depends(get_optional_user)):
    """获取当前用户偏好设置（登录用户按 user_id 隔离；游客返回全局/最近一条）。"""
    from db import get_db
    uid = user["id"] if user else None
    p = get_db().get_user_profile(user_id=uid) or {}
    return {
        "budget": p.get("budget", 20),
        "flavor_preferences": p.get("flavor_preferences", ""),
        "health_goals": p.get("health_goals", ""),
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
        flavor_preferences=req.flavor_preferences or "",
        health_goals=req.health_goals or "",
        user_id=uid,
    )
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        logger.warning("空消息被拒绝")
        raise HTTPException(status_code=400, detail="消息不能为空")

    session_id = req.session_id or str(uuid.uuid4())
    history = session_store.get(session_id)
    logger.info("chat 请求 | session=%s | msg=%s", session_id, req.message[:200])

    try:
        messages = history + [HumanMessage(content=req.message)]
        result = agent.invoke({"messages": messages})
        # last message is the final AI reply
        reply = clean_markdown(result["messages"][-1].content)
        # Token 统计（tiktoken 精确计数，回退字符估算）
        in_tokens = count_tokens(req.message) + count_messages(history)
        out_tokens = count_tokens(reply)
        add_tokens(in_tokens + out_tokens)
        logger.info("chat 成功 | session=%s | in_tokens=%s out_tokens=%s | reply_len=%s",
                    session_id, in_tokens, out_tokens, len(reply))
    except Exception as e:
        logger.exception("chat 失败 | session=%s | msg=%s | err=%s",
                         session_id, req.message[:200], e)
        reply = "抱歉，系统处理出错，请稍后再试或换一种问法。"

    # persist to memory (trim old turns)
    session_store.append(session_id, req.message, reply)

    return ChatResponse(reply=reply, session_id=session_id)


def _stream_reply(session_id: str, message: str):
    """真实流式输出：通过 agent.astream_events 逐 token 推送 LLM 生成内容。"""
    history = session_store.get(session_id)
    logger.info("chat/stream 请求 | session=%s | msg=%s", session_id, message[:200])
    messages = history + [HumanMessage(content=message)]

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
            async for event in agent.astream_events(
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
        add_tokens(count_tokens(message) + count_tokens(reply))
        session_store.append(session_id, message, reply)
        logger.info("chat/stream 完成 | session=%s | reply_len=%s", session_id, len(reply))
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """流式对话：SSE 输出，先 session 元数据，再 content 增量，最后 done。"""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    session_id = req.session_id or str(uuid.uuid4())
    return _stream_reply(session_id, req.message)


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
