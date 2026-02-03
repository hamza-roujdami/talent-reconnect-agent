"""FastAPI routes with SSE streaming for chat.

Uses Cosmos DB for session persistence (falls back to in-memory if not configured).
"""

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import AgentFactory
from sessions.cosmos_store import create_session_store


router = APIRouter()

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


async def stream_chat(
    factory: AgentFactory,
    store,
    message: str,
    session_id: str,
) -> AsyncIterator[str]:
    """Stream chat response as SSE events."""
    
    # Send session ID
    yield sse_event("session", {"session_id": session_id})
    
    # Get history before adding user message
    history = await store.get_history(session_id)
    
    # Add user message to history
    await store.add_message(session_id, "user", message)
    
    # Route to agent - use context-aware routing
    agent_key = factory.route(message)
    
    # Sticky routing: if user gives a short response and we were on profile,
    # stay on profile (they're likely adding details or confirming)
    if agent_key == "orchestrator" and history:
        last_agent = None
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("agent"):
                last_agent = msg.get("agent")
                break
        # FIRST: Check if user says "yes" to confirm profile → trigger search
        if last_agent == "profile" and message.lower().strip() in ["yes", "yes!", "looks good", "correct", "proceed", "go ahead", "search", "find them", "find candidates"]:
            agent_key = "search"
        # THEN: If short message and was on profile, stay with profile (adding details)
        elif last_agent == "profile" and len(message.split()) < 15:
            agent_key = "profile"
    
    agent_name = AGENT_NAMES.get(agent_key, agent_key)
    
    # Send agent activity
    yield sse_event("agent", {"name": agent_name, "key": agent_key})
    
    try:
        # Get response with conversation history
        response = await factory.chat(message, agent_key, history=history or None)
        
        # Stream the response
        yield sse_event("text", {"content": response})
        
        # Save assistant response to history
        await store.add_message(session_id, "assistant", response, agent=agent_key)
        
    except Exception as e:
        yield sse_event("error", {"message": str(e)})


# =============================================================================
# Shared Instances
# =============================================================================

_factory: AgentFactory | None = None
_store = None


async def get_factory() -> AgentFactory:
    """Get or create factory instance."""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
        await _factory.initialize()
    return _factory


async def get_store():
    """Get or create session store instance.
    
    Falls back to in-memory if Cosmos DB initialization fails.
    """
    global _store
    if _store is None:
        from sessions.cosmos_store import create_session_store, InMemorySessionStore
        
        store_instance = create_session_store()
        try:
            await store_instance.initialize()
            _store = store_instance
            print("✓ Using Cosmos DB session storage")
        except Exception as e:
            print(f"⚠️  Session store init failed: {e}")
            print("   Falling back to in-memory storage")
            _store = InMemorySessionStore()
            await _store.initialize()
            print("✓ Using in-memory session storage")
    return _store


# =============================================================================
# Routes
# =============================================================================

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response via SSE."""
    factory = await get_factory()
    store = await get_store()
    
    session_id = request.session_id or str(uuid.uuid4())
    
    return StreamingResponse(
        stream_chat(factory, store, request.message, session_id),
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
    store = await get_store()
    sessions = await store.list_sessions(limit=50)
    return {"sessions": sessions}


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get chat history for a session."""
    store = await get_store()
    session = await store.get_session(session_id)
    
    if not session:
        return {"messages": []}
    
    return {"messages": session.get("messages", [])}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    store = await get_store()
    deleted = await store.delete_session(session_id)
    
    if deleted:
        return {"status": "deleted"}
    return {"status": "not_found"}


@router.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    global _factory, _store
    
    if _factory:
        await _factory.cleanup()
        _factory = None
    
    if _store:
        await _store.close()
        _store = None
