"""
Agent Factory - Creates configured agent instances.
Multi-Agent (create_recruiting_workflow) - Handoff workflow with specialists

Supports LLM providers:
- azure_openai: Azure OpenAI (with Entra ID or API key auth)
- compass: Compass/Core42 API
"""
from pathlib import Path
from config import config
from tools.search_provider import build_search_context_provider
from tools.outreach_email import send_outreach_email


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
    """Create the single recruiter agent (simple mode).

    The recruiter is grounded by the Azure AI Search context provider so it can
    cite resumes directly from the knowledge base while still calling
    `send_outreach_email` when needed.
    """

    search_context = build_search_context_provider()

    return _create_client().create_agent(
        name="Recruiter",
        instructions=_load_instructions("recruiter"),
        context_providers=[search_context],
        tools=[send_outreach_email],
    )


def create_recruiting_workflow():
    """Create multi-agent recruiting workflow (advanced mode).
    
    Uses MAF HandoffBuilder for dynamic routing between specialists:
    - Orchestrator: Routes user requests
    - ProfileAgent: Generates ideal candidate profiles
    - SearchAgent: Searches Azure AI Search
    - InsightsAgent: Checks interview history & feedback
    - OutreachAgent: Drafts personalized emails
    
    Returns a Workflow that can be run with workflow.run_stream(messages).
    """
    from agent_framework import HandoffBuilder
    from agents.profile_agent import create_profile_agent
    from agents.search_agent import create_search_agent
    from agents.insights_agent import create_insights_agent
    from agents.outreach_agent import create_outreach_agent
    
    chat_client = _create_client()
    
    # Create specialist agents
    profile_agent = create_profile_agent(chat_client)
    search_agent = create_search_agent(chat_client, context_provider=build_search_context_provider())
    insights_agent = create_insights_agent(chat_client)
    outreach_agent = create_outreach_agent(chat_client)
    
    # Create orchestrator (coordinator agent)
    orchestrator = chat_client.create_agent(
        name="orchestrator",
        temperature=0.0,
        top_p=0.1,  # Very focused sampling
        instructions="""You are a silent router. Call ONE handoff tool and STOP.

ROUTING RULES:
1. Job/role request (e.g., "AI Engineer", "hire developer") → handoff_to_profile_agent
2. User approves profile ("yes", "ok", "looks good", "search", "find", "proceed") → handoff_to_search_agent
3. User wants to modify profile ("add", "change", "remove", "update") → handoff_to_profile_agent
4. User asks for candidate details/insights ("details", "more info", "show more") → handoff_to_search_agent
5. User asks about interview history, feedback, red flags, or "can we trust candidate X" → handoff_to_insights_agent
6. Email/contact/outreach/send request → handoff_to_outreach_agent

CRITICAL:
- DO NOT output any text, emojis, or messages
- DO NOT explain what you're doing
- ONLY call the appropriate handoff tool
- NEVER use emojis like 🎯📋✨
""",
    )
    
    # Build handoff workflow
    # - participants: All agents (orchestrator first as coordinator)
    # - set_coordinator: The orchestrator receives all user input first
    # - add_handoff: Enable routing (MUST include orchestrator's routes!)
    # NOTE: profile_agent does NOT have handoff to search - user must approve via orchestrator
    workflow = (
        HandoffBuilder(
            name="recruiting_workflow",
            participants=[orchestrator, profile_agent, search_agent, insights_agent, outreach_agent],
        )
        .set_coordinator(orchestrator)
        # Orchestrator exclusively routes user intent to the right specialist
        .add_handoff(orchestrator, [profile_agent, search_agent, insights_agent, outreach_agent])
        .build()
    )
    
    return workflow
