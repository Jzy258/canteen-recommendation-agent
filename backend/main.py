import asyncio
import json
import logging
import os
import uuid
from dotenv import load_dotenv

logger = logging.getLogger("canteen.agent")

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agent.agent import create_agent_executor
from middleware import RequestMetricsMiddleware, add_tokens, get_metrics

app = FastAPI(title="Canteen Recommendation Agent", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestMetricsMiddleware)

agent = create_agent_executor()

# session_id -> [HumanMessage / AIMessage, ...]
sessions: dict[str, list] = {}
MAX_HISTORY = 20


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """查看中间件统计：请求数 / 耗时 / Token。"""
    return get_metrics()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = req.session_id or str(uuid.uuid4())
    history = sessions.setdefault(session_id, [])

    try:
        messages = history + [HumanMessage(content=req.message)]
        result = agent.invoke({"messages": messages})
        # last message is the final AI reply
        reply = result["messages"][-1].content
        # 粗略 Token 统计（输入+输出字数 ≈ token）
        in_tokens = len(req.message) + sum(len(m.content) for m in history if m.content)
        out_tokens = len(reply) if reply else 0
        add_tokens(in_tokens + out_tokens)
    except Exception as e:
        logger.exception("chat failed: %s", e)
        reply = "抱歉，系统处理出错，请稍后再试或换一种问法。"

    # persist to memory (trim old turns)
    history.append(HumanMessage(content=req.message))
    history.append(AIMessage(content=reply))
    if len(history) > MAX_HISTORY:
        sessions[session_id] = history[-MAX_HISTORY:]

    return ChatResponse(reply=reply, session_id=session_id)


def _stream_reply(session_id: str, message: str):
    """流式生成回复，按字符切块 SSE 输出。"""
    history = sessions.setdefault(session_id, [])
    try:
        messages = history + [HumanMessage(content=message)]
        result = agent.invoke({"messages": messages})
        reply = result["messages"][-1].content
        add_tokens(len(message) + len(reply))
    except Exception as e:
        logger.exception("chat stream failed: %s", e)
        reply = "抱歉，系统处理出错，请稍后再试或换一种问法。"

    history.append(HumanMessage(content=message))
    history.append(AIMessage(content=reply))
    if len(history) > MAX_HISTORY:
        sessions[session_id] = history[-MAX_HISTORY:]

    async def gen():
        # 先发 session 元数据
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
        chunk_size = 4
        for i in range(0, len(reply), chunk_size):
            piece = reply[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'delta', 'content': piece}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)
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
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    session_id = req.session_id or str(uuid.uuid4())
    return _stream_reply(session_id, req.message)


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)