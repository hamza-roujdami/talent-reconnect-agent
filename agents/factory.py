"""
Agent Factory - Creates the multi-agent recruiting workflow.

Supports LLM providers:
- azure_openai: Azure OpenAI (with Entra ID or API key auth)
- compass: Compass/Core42 API
"""
import os
from pathlib import Path
from config import config
from agents.middleware import get_default_middleware


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


def create_recruiting_workflow(checkpoint_storage=None):
    """Create multi-agent recruiting workflow (advanced mode).
    
    Uses MAF HandoffBuilder for dynamic routing between specialists:
    - Orchestrator: Routes user requests
    - ProfileAgent: Generates ideal candidate profiles
    - SearchAgent: Searches Azure AI Search
    - InsightsAgent: Checks interview history & feedback
    - OutreachAgent: Drafts personalized emails
    
    Args:
        checkpoint_storage: Optional checkpoint storage for workflow persistence.
            Use FileCheckpointStorage or InMemoryCheckpointStorage from agent_framework.
            If None, checkpointing is disabled.
    
    Returns a Workflow that can be run with workflow.run_stream(messages).
    """
    from agent_framework import HandoffBuilder
    from agents.profile_agent import create_profile_agent
    from agents.search_agent import create_search_agent
    from agents.insights_agent import create_insights_agent
    from agents.outreach_agent import create_outreach_agent
    
    chat_client = _create_client()
    
    # Get middleware (logging + error handling)
    agent_middleware, function_middleware = get_default_middleware()
    enable_middleware = os.getenv("ENABLE_MIDDLEWARE", "true").lower() == "true"
    
    # Create specialist agents with middleware
    profile_agent = create_profile_agent(
        chat_client,
        middleware=agent_middleware if enable_middleware else None,
        function_middleware=function_middleware if enable_middleware else None,
    )
    search_agent = create_search_agent(
        chat_client,
        # No context_provider - uses search_candidates tool instead
        middleware=agent_middleware if enable_middleware else None,
        function_middleware=function_middleware if enable_middleware else None,
    )
    insights_agent = create_insights_agent(
        chat_client,
        middleware=agent_middleware if enable_middleware else None,
        function_middleware=function_middleware if enable_middleware else None,
    )
    outreach_agent = create_outreach_agent(
        chat_client,
        middleware=agent_middleware if enable_middleware else None,
        function_middleware=function_middleware if enable_middleware else None,
    )
    
    # Create orchestrator (coordinator agent)
    orchestrator = chat_client.as_agent(
        name="orchestrator",
        default_options={"temperature": 0.0, "top_p": 0.1},
        instructions="""You are a silent router. Call ONE handoff tool and STOP.

ROUTING RULES:
1. Job/role request (e.g., "AI Engineer", "hire developer") → handoff_to_rolecrafter
2. User approves profile ("yes", "ok", "looks good", "search", "find", "proceed") → handoff_to_talentscout
3. User wants to modify profile ("add", "change", "remove", "update") → handoff_to_rolecrafter
4. User asks for candidate details/insights ("details", "more info", "show more") → handoff_to_talentscout
5. User asks about interview history, feedback, red flags → handoff_to_insightpulse
6. Email/contact/outreach/send request → handoff_to_connectpilot

CRITICAL:
- DO NOT output any text, emojis, or messages
- DO NOT explain what you're doing
- ONLY call the appropriate handoff tool
- NEVER use emojis like 🎯📋✨
""",
    )
    
    # Build handoff workflow
    # - participants: All agents (orchestrator first as coordinator)
    # - with_start_agent: The orchestrator receives all user input first
    # - add_handoff: Enable routing between agents
    builder = (
        HandoffBuilder(
            name="recruiting_workflow",
            participants=[orchestrator, profile_agent, search_agent, insights_agent, outreach_agent],
        )
        .with_start_agent(orchestrator)
        # Orchestrator routes user intent to the right specialist
        .add_handoff(orchestrator, [profile_agent, search_agent, insights_agent, outreach_agent])
        # Specialists hand back to orchestrator when done (for next user input)
        .add_handoff(profile_agent, [orchestrator])
        .add_handoff(search_agent, [orchestrator])
        .add_handoff(insights_agent, [orchestrator])
        .add_handoff(outreach_agent, [orchestrator])
    )
    
    # Enable checkpointing if storage provided
    if checkpoint_storage is not None:
        builder = builder.with_checkpointing(checkpoint_storage)
    
    return builder.build()
