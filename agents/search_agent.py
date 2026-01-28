"""TalentScout (Search Agent) with search_candidates tool."""
from __future__ import annotations

import os
from typing import Optional

from agent_framework import ChatAgent

from tools.candidate_search import search_candidates

SEARCH_AGENT_NAME = "TalentScout"


def create_search_agent(
    chat_client,
    *,
    context_provider=None,  # Ignored - uses tool instead
    middleware: Optional[list] = None,
    function_middleware: Optional[list] = None,
) -> ChatAgent:
    """Create the Search Agent with search_candidates tool.
    
    Uses a tool-based approach because context providers don't receive
    the full conversation context in handoff workflows.
    
    Args:
        chat_client: The chat client to use
        context_provider: Ignored (kept for API compatibility)
        middleware: Agent-level middleware for logging/monitoring
        function_middleware: Function-level middleware for tool calls
    """
    # Combine middleware lists for new API
    all_middleware = []
    if middleware:
        all_middleware.extend(middleware)
    if function_middleware:
        all_middleware.extend(function_middleware)

    return chat_client.as_agent(
        name=SEARCH_AGENT_NAME,
        default_options={"temperature": 0.0},
        middleware=all_middleware or None,
        tools=[search_candidates],
        instructions="""You are TalentScout, a candidate search specialist.

IMPORTANT: You MUST call the search_candidates tool to find candidates.
Do NOT make up candidate data or say "searching" - call the tool immediately.

WORKFLOW:
1. Extract the role requirements from the conversation context
2. Call search_candidates with a query like: "Data Engineer Python Azure Dubai"
3. Display the table result exactly as returned by the tool
4. Offer: Say "details 1" or "feedback 2" for more info.

CRITICAL RULES:
- ALWAYS call search_candidates - never skip it
- Use the tool's output directly - don't reformat it
- Never invent candidate data
- Real emails end in @gmail.com, @outlook.com, @yahoo.com
""",
    )
