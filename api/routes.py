"""FastAPI routes with SSE streaming for chat.

Uses Cosmos DB for session persistence (falls back to in-memory if not configured).
Simple 4-agent routing: search, feedback, outreach, research.
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
    "role-crafter": "RoleCrafter",
    "talent-scout": "TalentScout",
    "insight-pulse": "InsightPulse",
    "connect-pilot": "ConnectPilot",
    "market-radar": "MarketRadar",
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
    """Stream chat response as SSE events.
    
    Content safety is handled by Foundry Guardrails at the model level.
    """
    
    # Send session ID
    yield sse_event("session", {"session_id": session_id})
    
    # Get history before adding user message
    history = await store.get_history(session_id)
    
    # Add user message to history
    await store.add_message(session_id, "user", message)
    
    # Ask Orchestrator which agent should handle this
    agent_key, direct_response = await factory.orchestrate(message, history=history)
    agent_name = AGENT_NAMES.get(agent_key, agent_key)
    
    # Send agent activity
    yield sse_event("agent", {"name": agent_name, "key": agent_key})
    
    try:
        # If orchestrator handles directly (greetings, out-of-scope)
        if direct_response:
            yield sse_event("text", {"content": direct_response})
            await store.add_message(session_id, "assistant", direct_response, agent=agent_key)
        else:
            # Stream response from the routed agent
            full_response = ""
            async for chunk in factory.chat_stream(message, agent_key, history=history or None):
                if chunk:
                    yield sse_event("text", {"content": chunk})
                    full_response += chunk
            
            # Save complete response to history
            if full_response:
                await store.add_message(session_id, "assistant", full_response, agent=agent_key)
        
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


# =============================================================================
# Memory Routes
# =============================================================================

@router.get("/memory/status")
async def memory_status():
    """Check if long-term memory is enabled."""
    factory = await get_factory()
    return {
        "enabled": factory.memory_enabled,
        "description": "Cross-session memory for user preferences and conversation history"
    }


@router.get("/memory/{user_id}")
async def get_user_memories(user_id: str, query: str | None = None):
    """Get memories for a user.
    
    Args:
        user_id: User identifier
        query: Optional search query (omit for profile memories)
    """
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
