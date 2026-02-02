"""FastAPI routes with SSE streaming for chat."""

import json
import uuid
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import AgentFactory


router = APIRouter()

# In-memory session storage (use Redis/DB in production)
sessions: dict[str, dict] = {}

# Agent display names
AGENT_NAMES = {
    "orchestrator": "Orchestrator",
    "profile": "Profile Agent",
    "search": "Search Agent",
    "insights": "Insights Agent",
    "outreach": "Outreach Agent",
}


class ChatRequest(BaseModel):
    """Chat request body."""
    message: str
    session_id: str | None = None


class SessionInfo(BaseModel):
    """Session metadata."""
    id: str
    title: str | None
    message_count: int
    created_at: str
    updated_at: str


# =============================================================================
# SSE Helpers
# =============================================================================

def sse_event(event_type: str, data: dict) -> str:
    """Format SSE event."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


async def stream_chat(factory: AgentFactory, message: str, session_id: str) -> AsyncIterator[str]:
    """Stream chat response as SSE events."""
    
    # Get or create session
    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "title": None,
            "messages": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
    
    session = sessions[session_id]
    
    # Send session ID
    yield sse_event("session", {"session_id": session_id})
    
    # Add user message to history
    session["messages"].append({"role": "user", "content": message})
    
    # Set title from first message
    if not session["title"]:
        session["title"] = message[:50] + ("..." if len(message) > 50 else "")
    
    # Route to agent
    agent_key = factory.route(message)
    agent_name = AGENT_NAMES.get(agent_key, agent_key)
    
    # Send agent activity
    yield sse_event("agent", {"name": agent_name, "key": agent_key})
    
    try:
        # Get response (streaming would be ideal, but using simple for now)
        response = await factory.chat(message, agent_key)
        
        # Stream the response
        yield sse_event("text", {"content": response})
        
        # Save to history
        session["messages"].append({
            "role": "assistant",
            "content": response,
            "agent": agent_key,
        })
        session["updated_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        yield sse_event("error", {"message": str(e)})


# =============================================================================
# Routes
# =============================================================================

# Shared factory instance
_factory: AgentFactory | None = None


async def get_factory() -> AgentFactory:
    """Get or create factory instance."""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
        await _factory.initialize()
    return _factory


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response via SSE."""
    factory = await get_factory()
    
    session_id = request.session_id or str(uuid.uuid4())
    
    return StreamingResponse(
        stream_chat(factory, request.message, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
async def list_sessions():
    """List all chat sessions."""
    session_list = []
    for sid, session in sorted(
        sessions.items(),
        key=lambda x: x[1].get("updated_at", ""),
        reverse=True,
    ):
        session_list.append({
            "id": sid,
            "title": session.get("title"),
            "message_count": len(session.get("messages", [])),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
        })
    return {"sessions": session_list}


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get chat history for a session."""
    session = sessions.get(session_id)
    if not session:
        return {"messages": []}
    return {"messages": session.get("messages", [])}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted"}
    return {"status": "not_found"}


@router.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    global _factory
    if _factory:
        await _factory.cleanup()
        _factory = None
