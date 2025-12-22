"""
Agent Factory - Creates configured agent instances.

Supports two modes:
1. Single Agent (create_recruiter) - Simple, all-in-one agent
2. Multi-Agent (create_recruiting_workflow) - Handoff workflow with specialists

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
    """Create single Recruiter agent (simple mode).
    
    Uses semantic search (BM25 + Neural reranking) for best relevance.
    
    This is the all-in-one agent that handles the entire recruiting workflow:
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


def create_recruiting_workflow():
    """Create multi-agent recruiting workflow (advanced mode).
    
    Uses MAF HandoffBuilder for dynamic routing between specialists:
    - Orchestrator: Routes user requests
    - ProfileAgent: Generates ideal candidate profiles
    - SearchAgent: Searches Azure AI Search
    - ScoringAgent: Re-ranks with feedback history
    - OutreachAgent: Drafts personalized emails
    
    Returns a Workflow that can be run with workflow.run_stream(messages).
    """
    from agent_framework import HandoffBuilder
    from agents.profile_agent import create_profile_agent
    from agents.search_agent import create_search_agent
    from agents.scoring_agent import create_scoring_agent
    from agents.outreach_agent import create_outreach_agent
    
    chat_client = _create_client()
    
    # Create specialist agents
    profile_agent = create_profile_agent(chat_client)
    search_agent = create_search_agent(chat_client)
    scoring_agent = create_scoring_agent(chat_client)
    outreach_agent = create_outreach_agent(chat_client)
    
    # Create orchestrator (coordinator agent)
    orchestrator = chat_client.create_agent(
        name="orchestrator",
        instructions="""You are a recruiting assistant. Your job is to understand what the user 
wants and delegate to the right specialist.

## Your Specialists

1. **profile_agent** - Call when user describes a role to hire for
   - Generates an "ideal candidate" profile with skills, experience, location
   - Call this FIRST when user wants to hire someone new

2. **search_agent** - Call to search the resume database
   - Has tools: search_resumes_semantic, get_candidate_details, show_skill_comparison
   - Call after profile_agent has created the ideal profile
   - Or directly if user asks to search/find candidates

3. **scoring_agent** - Call to check interview history and re-rank candidates
   - Fetches past interview feedback for candidates
   - Applies bonuses for previous "strong hire" recommendations
   - Flags red flags from previous "no hire" decisions
   - Call after search_agent returns candidates

4. **outreach_agent** - Call when user wants to contact a candidate
   - Drafts personalized recruitment emails
   - Call when user says "contact", "email", "reach out"

## Routing Examples

- "Hire a senior AI engineer in Dubai" → handoff_to_profile_agent
- "Search for Python developers" → handoff_to_search_agent  
- "Check their interview history" → handoff_to_scoring_agent
- "Show me details for #1 and #3" → handoff_to_search_agent
- "Contact candidate #2" → handoff_to_outreach_agent
- "Compare skills" → handoff_to_search_agent
- "What can you do?" → Answer directly (no handoff)

## Recommended Flow

For new hiring requests:
1. profile_agent (generate ideal profile)
2. search_agent (find candidates)
3. scoring_agent (check history, re-rank)
4. outreach_agent (contact selected candidates)

## Guidelines

- For new hiring requests, ALWAYS start with profile_agent
- After search returns candidates, suggest checking interview history
- Be brief when handing off - the specialist will handle the details
- After specialists complete, summarize if needed
""",
    )
    
    # Build handoff workflow
    # - participants: All agents (orchestrator first as coordinator)
    # - set_coordinator: The orchestrator receives all user input first
    workflow = (
        HandoffBuilder(
            name="recruiting_workflow",
            participants=[orchestrator, profile_agent, search_agent, scoring_agent, outreach_agent],
        )
        .set_coordinator("orchestrator")
        .build()
    )
    
    return workflow
