import os
import uuid
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agent.agent import create_agent_executor

app = FastAPI(title="Canteen Recommendation Agent", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    except Exception as e:
        reply = f"Sorry, an error occurred: {str(e)}"

    # persist to memory (trim old turns)
    history.append(HumanMessage(content=req.message))
    history.append(AIMessage(content=reply))
    if len(history) > MAX_HISTORY:
        sessions[session_id] = history[-MAX_HISTORY:]

    return ChatResponse(reply=reply, session_id=session_id)


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)