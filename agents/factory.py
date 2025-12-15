"""
Agent Factory - Creates configured agent instances.
"""
from pathlib import Path
from agent_framework.openai import OpenAIChatClient
from config import config
from tools.search import search_resumes
from tools.email import send_outreach_email


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


def create_recruiter():
    """Create Recruiter agent with all tools.
    
    This is the main agent that orchestrates the recruiting workflow:
    1. Understand job requirements
    2. Generate job description
    3. Search resumes in Azure AI Search
    4. Draft outreach emails
    """
    return _create_client().create_agent(
        name="Recruiter",
        instructions=_load_instructions("recruiter"),
        tools=[search_resumes, send_outreach_email],
    )
