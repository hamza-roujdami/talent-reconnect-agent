"""FastAPI routes for the Talent Reconnect chat API.

Provides:
- SSE streaming chat endpoint
- Session management (list, history, delete)
- Memory management (status, get, delete)

Uses Cosmos DB for session persistence (falls back to in-memory).
"""

import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import AgentFactory
from sessions.cosmos_store import create_session_store, InMemorySessionStore


router = APIRouter()


# =============================================================================
# Constants & Models
# =============================================================================

# Maps agent keys to display names for the UI
AGENT_NAMES = {
    "orchestrator": "Orchestrator",
    "role-crafter": "RoleCrafter",
    "talent-scout": "TalentScout",
    "insight-pulse": "InsightPulse",
    "connect-pilot": "ConnectPilot",
    "market-radar": "MarketRadar",
}


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str
    session_id: str | None = None


# =============================================================================
# Singleton Instances
# =============================================================================

_factory: AgentFactory | None = None
_store = None


async def get_factory() -> AgentFactory:
    """Get or create the agent factory singleton."""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
        await _factory.initialize()
    return _factory


async def get_store():
    """Get or create the session store singleton.
    
    Falls back to in-memory storage if Cosmos DB fails.
    """
    global _store
    if _store is None:
        store = create_session_store()
        try:
            await store.initialize()
            _store = store
            print("✓ Using Cosmos DB sessions")
        except Exception as e:
            print(f"⚠️ Cosmos DB failed: {e}")
            _store = InMemorySessionStore()
            await _store.initialize()
            print("✓ Using in-memory sessions")
    return _store


# =============================================================================
# SSE Streaming
# =============================================================================

def sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


async def stream_chat(factory: AgentFactory, store, message: str, session_id: str):
    """Stream chat response as SSE events.
    
    Event types:
        - session: Contains session_id
        - agent: Which agent is handling the message
        - text: Response text chunk
        - error: Error message
    """
    # Send session ID first
    yield sse_event("session", {"session_id": session_id})
    
    # Get conversation history and add user message
    history = await store.get_history(session_id)
    await store.add_message(session_id, "user", message)
    
    # Route to appropriate agent
    agent_key, direct_response = await factory.orchestrate(message, history=history)
    agent_name = AGENT_NAMES.get(agent_key, agent_key)
    yield sse_event("agent", {"name": agent_name, "key": agent_key})
    
    try:
        if direct_response:
            # Orchestrator handled directly (greetings, out-of-scope)
            yield sse_event("text", {"content": direct_response})
            await store.add_message(session_id, "assistant", direct_response, agent=agent_key)
        else:
            # Stream from the routed agent
            full_response = ""
            async for chunk in factory.chat_stream(message, agent_key, history=history or None, user_id=session_id):
                if chunk:
                    yield sse_event("text", {"content": chunk})
                    full_response += chunk
            
            if full_response:
                await store.add_message(session_id, "assistant", full_response, agent=agent_key)
                
    except Exception as e:
        yield sse_event("error", {"message": str(e)})


# =============================================================================
# Chat Routes
# =============================================================================

@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Stream chat response via Server-Sent Events."""
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


# =============================================================================
# Session Routes
# =============================================================================

@router.get("/sessions")
async def list_sessions():
    """List all chat sessions (most recent first)."""
    store = await get_store()
    sessions = await store.list_sessions(limit=50)
    return {"sessions": sessions}


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get message history for a session."""
    store = await get_store()
    session = await store.get_session(session_id)
    return {"messages": session.get("messages", []) if session else []}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    store = await get_store()
    deleted = await store.delete_session(session_id)
    return {"status": "deleted" if deleted else "not_found"}


# =============================================================================
# Memory Routes (Long-term, Cross-session)
# =============================================================================

@router.get("/memory/status")
async def memory_status():
    """Check if long-term memory is enabled."""
    factory = await get_factory()
    return {"enabled": factory.memory_enabled}


@router.get("/memory/{user_id}")
async def get_user_memories(user_id: str, query: str | None = None):
    """Get memories for a user. Optional query to search specific memories."""
    factory = await get_factory()
    if not factory.memory_enabled:
        return {"error": "Memory not enabled", "memories": []}
    
    memories = await factory.get_user_memories(user_id, query)
    return {"user_id": user_id, "memories": memories}


@router.delete("/memory/{user_id}")
async def delete_user_memories(user_id: str):
    """Delete all memories for a user (GDPR compliance)."""
    factory = await get_factory()
    if not factory.memory_enabled:
        return {"error": "Memory not enabled", "deleted": False}
    
    deleted = await factory.delete_user_memories(user_id)
    return {"user_id": user_id, "deleted": deleted}


# =============================================================================
# Lifecycle
# =============================================================================

@router.on_event("shutdown")
async def shutdown():
    """Cleanup connections on shutdown."""
    global _factory, _store
    
    if _factory:
        await _factory.cleanup()
        _factory = None
    
    if _store:
        await _store.close()
        _store = None
