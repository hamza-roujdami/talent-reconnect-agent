"""
FastAPI routes for Talent Reconnect API.

Provides REST endpoints with streaming support.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, AsyncGenerator, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_framework import ChatMessage, FunctionCallContent, Role
from workflow import create_workflow
from config import config

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Search mode from environment (default: semantic)
import os
SEARCH_MODE = os.environ.get("SEARCH_MODE", "semantic")


# --- Models ---

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


# --- Session Management ---

class Session:
    """User session with conversation history."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.agent = create_workflow(search_mode=SEARCH_MODE)
        self.messages: List[ChatMessage] = []
        self.history: List[dict] = []  # For UI display
        self.title: Optional[str] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


sessions: Dict[str, Session] = {}


def get_or_create_session(session_id: str = None) -> Session:
    """Get existing session or create new one."""
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    new_id = session_id or str(uuid.uuid4())
    session = Session(new_id)
    sessions[new_id] = session
    return session


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup."""
    print("🔧 Initializing Talent Reconnect Agent...")
    print(f"✅ Resume database: Azure AI Search")
    print(f"   Index: {config.search.index}")
    print(f"🤖 Model: {config.llm.model}")
    print(f"🌐 Server: http://localhost:8000\n")
    yield
    print("\n🔧 Shutting down...")


app = FastAPI(
    title="Talent Reconnect API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---

@app.get("/")
async def root():
    """Serve chat UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    """Health check."""
    return {
        "service": "Talent Reconnect Agent",
        "status": "healthy",
        "model": config.llm.model,
        "sessions": len(sessions),
    }


@app.get("/sessions")
async def list_sessions():
    """List all sessions."""
    return {
        "sessions": [
            {
                "id": s.session_id,
                "title": s.title or "New Conversation",
                "message_count": len(s.history),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sorted(sessions.values(), key=lambda x: x.updated_at, reverse=True)
        ]
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
    return {"deleted": True}


@app.get("/session/{session_id}/history")
async def get_history(session_id: str):
    """Get chat history."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return {"messages": sessions[session_id].history}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Process message with streaming response."""
    
    async def generate() -> AsyncGenerator[str, None]:
        session = get_or_create_session(request.session_id)
        
        # Send session ID
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"
        
        # Update session
        session.updated_at = datetime.now()
        if not session.title:
            session.title = request.message[:50] + ("..." if len(request.message) > 50 else "")
        
        # Add user message
        session.messages.append(ChatMessage("user", text=request.message))
        session.history.append({"role": "user", "text": request.message})
        
        try:
            response_text = ""
            
            async for event in session.agent.run_stream(session.messages):
                # Stream tool calls
                if hasattr(event, 'contents'):
                    for item in event.contents:
                        if isinstance(item, FunctionCallContent) and item.name:
                            yield f"data: {json.dumps({'type': 'tool', 'name': item.name})}\n\n"
                
                # Collect response (event.text is delta/incremental)
                if hasattr(event, 'text') and event.text:
                    response_text += event.text
            
            # Send final response
            if response_text:
                yield f"data: {json.dumps({'type': 'text', 'content': response_text})}\n\n"
                session.messages.append(ChatMessage("assistant", text=response_text))
                session.history.append({"role": "assistant", "text": response_text})
            
        except Exception as e:
            logger.exception("Stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
