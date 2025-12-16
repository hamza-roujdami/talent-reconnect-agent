"""
Agent Factory - Creates configured agent instances.

Supports different search modes:
- bm25: Fast keyword matching
- semantic: Neural reranking (+15-25% relevance)
"""
from pathlib import Path
from typing import Literal
from agent_framework.openai import OpenAIChatClient
from config import config
from tools.search_bm25 import search_resumes_bm25
from tools.search_semantic import search_resumes_semantic
from tools.email import send_outreach_email


# Search mode type
SearchMode = Literal["bm25", "semantic"]


def _load_instructions(name: str) -> str:
    """Load agent instructions from markdown file."""
    path = Path(__file__).parent.parent / "instructions" / f"{name}.md"
    return path.read_text() if path.exists() else f"You are the {name} agent."


def _create_client() -> OpenAIChatClient:
    """Create OpenAI-compatible chat client."""
    return OpenAIChatClient(
        model_id=config.llm.model,
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
    )


def _get_search_tool(mode: SearchMode):
    """Get the search tool for the specified mode."""
    if mode == "semantic":
        return search_resumes_semantic
    else:
        return search_resumes_bm25


def create_recruiter(search_mode: SearchMode = "semantic"):
    """Create Recruiter agent with configurable search.
    
    Args:
        search_mode: Which search backend to use:
            - "bm25": Fast keyword matching
            - "semantic": Neural reranking (+15-25%, default)
    
    This is the main agent that orchestrates the recruiting workflow:
    1. Understand job requirements
    2. Generate job description
    3. Search resumes in Azure AI Search
    4. Draft outreach emails
    """
    search_tool = _get_search_tool(search_mode)
    
    return _create_client().create_agent(
        name="Recruiter",
        instructions=_load_instructions("recruiter"),
        tools=[search_tool, send_outreach_email],
    )
