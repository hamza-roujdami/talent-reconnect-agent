"""
Agent Factory - Creates configured agent instances.

Search: Semantic search with BM25 + Neural reranking

Supports LLM providers:
- azure_openai: Azure OpenAI (with Entra ID or API key auth)
- compass: Compass/Core42 API
"""
from pathlib import Path
from config import config
from tools.search_semantic import search_resumes_semantic, get_candidate_details, show_skill_comparison
from tools.email import send_outreach_email


def _load_instructions(name: str) -> str:
    """Load agent instructions from markdown file."""
    path = Path(__file__).parent.parent / "instructions" / f"{name}.md"
    return path.read_text() if path.exists() else f"You are the {name} agent."


def _create_client():
    """Create chat client based on config."""
    llm = config.llm
    
    if llm.provider == "azure_openai":
        from agent_framework.azure import AzureOpenAIChatClient
        
        if llm.use_entra_id:
            # Azure OpenAI with Entra ID (Azure AD) authentication
            from azure.identity import DefaultAzureCredential
            
            return AzureOpenAIChatClient(
                endpoint=llm.azure_endpoint,
                deployment_name=llm.azure_deployment,
                credential=DefaultAzureCredential(),
                api_version="2024-10-21",
            )
        else:
            # Azure OpenAI with API key
            return AzureOpenAIChatClient(
                endpoint=llm.azure_endpoint,
                deployment_name=llm.azure_deployment,
                api_key=llm.api_key,
                api_version="2024-10-21",
            )
    else:
        # Compass or OpenAI compatible endpoint
        from agent_framework.openai import OpenAIChatClient
        
        return OpenAIChatClient(
            model_id=llm.model,
            api_key=llm.api_key,
            base_url=llm.base_url,
        )


def create_recruiter():
    """Create Recruiter agent.
    
    Uses semantic search (BM25 + Neural reranking) for best relevance.
    
    This is the main agent that orchestrates the recruiting workflow:
    1. Understand job requirements
    2. Generate job description
    3. Search resumes in Azure AI Search
    4. Drill down into candidate details
    5. Draft outreach emails
    """
    return _create_client().create_agent(
        name="Recruiter",
        instructions=_load_instructions("recruiter"),
        tools=[search_resumes_semantic, get_candidate_details, show_skill_comparison, send_outreach_email],
    )
