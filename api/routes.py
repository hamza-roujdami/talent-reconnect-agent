"""
FastAPI routes for Talent Reconnect API.

Multi-agent workflow with streaming support.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, AsyncGenerator, List, Optional, Tuple
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_framework import (
    AgentRunUpdateEvent,
    FunctionCallContent,
    FunctionResultContent,
    WorkflowOutputEvent,
    RequestInfoEvent,
    HandoffUserInputRequest,
)
from agents.factory import create_recruiting_workflow
from config import config

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent.parent / "static"

PROFILE_AGENT_NAME = "RoleCrafter"
SEARCH_AGENT_NAME = "TalentScout"
INSIGHTS_AGENT_NAME = "InsightPulse"
OUTREACH_AGENT_NAME = "ConnectPilot"

TOOL_FOLLOW_UPS = {
    "lookup_feedback_by_emails": "Curious about someone else? Tell me which candidate number to check or share their email.",
    "lookup_feedback_by_ids": "Need references on more people? Ask for other candidate numbers or say 'log new feedback'.",
    "log_interview_feedback": "All set. Want me to check history for another candidate or draft outreach next?",
    "send_outreach_email": "Need edits or want to reach out to another candidate? I can draft as many emails as you need.",
}


def _handoff_name(agent_name: str) -> str:
    return f"handoff_to_{agent_name.replace(' ', '').lower()}"


HANDOFF_TO_ROLECRAFTER = _handoff_name(PROFILE_AGENT_NAME)
HANDOFF_TO_TALENTSCOUT = _handoff_name(SEARCH_AGENT_NAME)
HANDOFF_TO_INSIGHTPULSE = _handoff_name(INSIGHTS_AGENT_NAME)
HANDOFF_TO_CONNECTPILOT = _handoff_name(OUTREACH_AGENT_NAME)


# --- Models ---
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


# --- Session Management ---

PENDING_REQUEST_TTL = timedelta(minutes=2)


class Session:
    """User session with multi-agent workflow."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.workflow = create_recruiting_workflow()
        self.pending_requests: List[Tuple[HandoffUserInputRequest, datetime]] = []
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


def _prune_pending_requests(session: Session) -> None:
    if not session.pending_requests:
        return
    cutoff = datetime.now() - PENDING_REQUEST_TTL
    session.pending_requests = [
        (req, created_at)
        for (req, created_at) in session.pending_requests
        if created_at >= cutoff
    ]


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup."""
    print("🔧 Initializing Talent Reconnect - Multi-Agent Mode")
    print(f"✅ Agents: Orchestrator → Profile → Search → Insights → Outreach")
    print(f"✅ Resume database: Azure AI Search ({config.search.index})")
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
    """Process message with multi-agent workflow streaming."""
    
    async def generate() -> AsyncGenerator[str, None]:
        session = get_or_create_session(request.session_id)
        
        # Send session ID
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"
        
        # Update session
        session.updated_at = datetime.now()
        if not session.title:
            session.title = request.message[:50] + ("..." if len(request.message) > 50 else "")
        
        # Add user message to history
        session.history.append({"role": "user", "text": request.message})

        # Drop stale pending requests so old prompts don't hijack new conversations
        _prune_pending_requests(session)
        
        try:
            # Choose workflow method based on pending requests
            if session.pending_requests:
                responses = {req.request_id: request.message for (req, _) in session.pending_requests}
                session.pending_requests = []
                stream = session.workflow.send_responses_streaming(responses)
            else:
                stream = session.workflow.run_stream(request.message)
            
            response_text = ""
            fallback_blocked_text = None  # Last blocked snippet, in case nothing else streams
            seen_tools = set()  # Track which tools we've announced
            seen_agents = set()  # Track which agents we've announced
            showed_tool_result = False  # Track if we showed a substantial tool result
            profile_buffer = ""  # Buffer for RoleCrafter output
            current_agent = None  # Track current agent
            tool_call_names = {}  # Map call_id -> tool name for follow-ups
            
            async for event in stream:
                # Stream tool calls and results from AgentRunUpdateEvent
                if isinstance(event, AgentRunUpdateEvent):
                    # Announce agent (only once per agent)
                    agent_name = event.executor_id
                    if agent_name and agent_name not in seen_agents:
                        seen_agents.add(agent_name)
                        current_agent = agent_name
                        # Format agent name nicely
                        display_name = agent_name.replace('_', ' ').title()
                        yield f"data: {json.dumps({'type': 'agent', 'name': display_name})}\n\n"
                        
                        # If switching away from RoleCrafter, flush the buffer
                        if profile_buffer and agent_name != PROFILE_AGENT_NAME:
                            yield f"data: {json.dumps({'type': 'text', 'content': profile_buffer})}\n\n"
                            response_text += profile_buffer
                            profile_buffer = ""
                    data = event.data
                    if hasattr(data, 'contents') and data.contents:
                        for item in data.contents:
                            # Stream tool call announcement (only once per tool)
                            if isinstance(item, FunctionCallContent) and item.name:
                                # Skip handoff tools, only show actual tools
                                if not item.name.startswith('handoff_') and item.name not in seen_tools:
                                    seen_tools.add(item.name)
                                    yield f"data: {json.dumps({'type': 'tool', 'name': item.name})}\n\n"
                                if getattr(item, 'call_id', None):
                                    tool_call_names[item.call_id] = item.name
                                
                                # Extract profile card from TalentScout handoff context
                                if item.name == HANDOFF_TO_TALENTSCOUT and item.arguments:
                                    try:
                                        import json as json_mod
                                        args = json_mod.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                                        context = args.get('context', '')
                                        # If context contains profile card markers, show it
                                        if '🎯' in context or '📋' in context:
                                            yield f"data: {json.dumps({'type': 'text', 'content': context})}\n\n"
                                    except:
                                        pass
                            
                            # Stream tool results that contain actual content (tables, candidates)
                            if isinstance(item, FunctionResultContent) and item.result:
                                result_str = str(item.result)
                                tool_name = tool_call_names.get(getattr(item, 'call_id', None))
                                # Show substantial tool output like tables, candidate lists, or email drafts
                                should_show_result = (
                                    ('|' in result_str or 'Candidate' in result_str)
                                    or (tool_name == 'send_outreach_email')
                                ) and 'handoff_to' not in result_str

                                if should_show_result:
                                    yield f"data: {json.dumps({'type': 'tool_result', 'content': result_str})}\n\n"
                                    showed_tool_result = True
                                    follow_up = TOOL_FOLLOW_UPS.get(tool_name)
                                    if follow_up:
                                        yield f"data: {json.dumps({'type': 'text', 'content': follow_up})}\n\n"
                                        session.history.append({"role": "assistant", "text": follow_up})
                    
                    if hasattr(data, 'text') and data.text:
                        text = data.text
                        
                        if showed_tool_result:
                            continue
                        
                        block_patterns = [
                            'let me know',
                            'anything else',
                            'if there\'s',
                            'if there is',
                            'happy to help',
                            'feel free',
                            'is there anything',
                            'would you like',
                            'i can help',
                            'seems there is no',
                            'it seems',
                            'handoff',
                            'handed',
                            'passed',
                            'forwarded',
                            'explore or add',
                            'i\'ve sent',
                            'sent off',
                            'let me pass',
                            'pass this',
                            'calling',
                            'request shared',
                            'will update',
                            'while we wait',
                            'great!',
                            'perfect!',
                            'excellent!',
                            'search agent',
                            'profile agent',
                            'outreach agent',
                            'rolecrafter',
                            'role crafter',
                            'talentscout',
                            'talent scout',
                            'insightpulse',
                            'insight pulse',
                            'connectpilot',
                            'connect pilot',
                            'i found',
                            'here are',
                            'found the following',
                            'matching candidates',
                            'suitable candidates',
                            'top candidates',
                            # Routing confirmations
                            'your request',
                            'has been routed',
                            'been over to',
                            'for further assistance',
                            'routed',
                            'i\'ve routed',
                            'they\'ll assist',
                            'assist you further',
                            'done!',
                            'successfully',
                            'complete',
                            'specialist',
                            'transferred',
                            'transfer',
                            'handling',
                            'expert assistance',
                        ]
                        should_block = any(p in text.lower() for p in block_patterns)
                        
                        if agent_name == PROFILE_AGENT_NAME:
                            if not should_block:
                                profile_buffer += text
                            elif not response_text:
                                snippet = text.strip()
                                if len(snippet) >= 12:
                                    fallback_blocked_text = snippet
                            continue
                        
                        if not should_block and text.strip():
                            response_text += text
                            fallback_blocked_text = None
                        elif should_block and text.strip() and not response_text:
                            snippet = text.strip()
                            if len(snippet) >= 12:
                                fallback_blocked_text = snippet
                
                # Handle pending user input requests
                if isinstance(event, RequestInfoEvent):
                    session.pending_requests.append((event, datetime.now()))
                
                # Handle final workflow output (usually empty if we streamed everything)
                if isinstance(event, WorkflowOutputEvent):
                    pass  # Already streamed via AgentRunUpdateEvent
            
            # Flush profile buffer if anything left
            if profile_buffer:
                yield f"data: {json.dumps({'type': 'text', 'content': profile_buffer})}\n\n"
                session.history.append({"role": "assistant", "text": profile_buffer})
                profile_buffer = ""  # Clear buffer
            
            # Send final accumulated text if any (and no tool result was shown)
            # Skip if we already sent profile content
            if response_text and not showed_tool_result:
                # Final filter - only block obvious routing messages
                final_block_patterns = [
                    'your request has been',
                    'forwarded to the',
                    'handed off to',
                    'transferred to the',
                    'routed to the',
                ]
                should_block_final = any(p in response_text.lower() for p in final_block_patterns)
                if not should_block_final:
                    yield f"data: {json.dumps({'type': 'text', 'content': response_text})}\n\n"
                    session.history.append({"role": "assistant", "text": response_text})
            elif fallback_blocked_text and not showed_tool_result:
                yield f"data: {json.dumps({'type': 'text', 'content': fallback_blocked_text})}\n\n"
                session.history.append({"role": "assistant", "text": fallback_blocked_text})
            
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
