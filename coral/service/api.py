from typing import Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="CORAL Service API", description="Backend service for Chat-to-CORAL", version="1.0.0"
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    messages: list[Message]
    config: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    session_id: str
    status: str
    message: str


def trigger_meta_agent_and_coral(session_id: str, request_data: dict) -> None:
    """
    Stub function for background task to trigger the meta agent and start the CORAL process.
    """
    print(f"Background task started for session_id: {session_id}")
    # TODO: Implement meta agent logic, generate CORAL configuration, and spawn agents
    pass


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Receive chat message, trigger background CORAL generation.
    """
    try:
        background_tasks.add_task(
            trigger_meta_agent_and_coral, request.session_id, request.model_dump()
        )
        return ChatResponse(
            session_id=request.session_id,
            status="accepted",
            message="Request received. Processing in background.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{session_id}")
async def get_status(session_id: str):
    """
    Get status of a Chat-to-CORAL session.
    """
    return {
        "session_id": session_id,
        "status": "pending",
        "details": "Status check not fully implemented yet.",
    }
