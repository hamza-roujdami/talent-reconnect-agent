"""Agent definitions builder.

Assembles all agent configurations with appropriate tools.
"""

import os

from azure.ai.projects.models import (
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
)

from . import orchestrator, profile, search, insights, outreach
from .tools import SEARCH_CANDIDATES_TOOL, LOOKUP_FEEDBACK_TOOL, SEND_EMAIL_TOOL


# Index names (from env)
RESUME_INDEX = os.environ.get("SEARCH_RESUME_INDEX", "resumes")
FEEDBACK_INDEX = os.environ.get("SEARCH_FEEDBACK_INDEX", "feedback")


def get_agent_definitions(
    search_connection_id: str = None,
    use_builtin_search: bool = False,
) -> dict:
    """Build agent definitions with search tools.
    
    Args:
        search_connection_id: Foundry connection ID for Azure AI Search
        use_builtin_search: Whether to use built-in AzureAISearchAgentTool
        
    Returns:
        Dict mapping agent key to config (instructions, tools)
    """
    
    if use_builtin_search and search_connection_id:
        # Built-in Azure AI Search tools (Foundry executes search)
        resume_search_tool = AzureAISearchAgentTool(
            azure_ai_search=AzureAISearchToolResource(
                indexes=[
                    AISearchIndexResource(
                        project_connection_id=search_connection_id,
                        index_name=RESUME_INDEX,
                        query_type=AzureAISearchQueryType.SEMANTIC,
                    ),
                ]
            )
        )
        
        feedback_search_tool = AzureAISearchAgentTool(
            azure_ai_search=AzureAISearchToolResource(
                indexes=[
                    AISearchIndexResource(
                        project_connection_id=search_connection_id,
                        index_name=FEEDBACK_INDEX,
                        query_type=AzureAISearchQueryType.SEMANTIC,
                    ),
                ]
            )
        )
    else:
        # FunctionTool approach (we execute search ourselves)
        resume_search_tool = SEARCH_CANDIDATES_TOOL
        feedback_search_tool = LOOKUP_FEEDBACK_TOOL
    
    return {
        "orchestrator": orchestrator.get_config(),
        "profile": profile.get_config(),
        "search": search.get_config(resume_search_tool, use_builtin_search),
        "insights": insights.get_config(feedback_search_tool, use_builtin_search),
        "outreach": outreach.get_config(email_tool=SEND_EMAIL_TOOL),
    }


# List of all agent keys
AGENT_KEYS = ["orchestrator", "profile", "search", "insights", "outreach"]
