"""Agent definitions builder.

Assembles all agent configurations with built-in Azure AI Search tools.
"""

import os

from azure.ai.projects.models import (
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
)

from . import orchestrator, profile, search, insights, outreach
from .tools import SEND_EMAIL_TOOL


# Index names (from env)
RESUME_INDEX = os.environ.get("SEARCH_RESUME_INDEX", "resumes")
FEEDBACK_INDEX = os.environ.get("SEARCH_FEEDBACK_INDEX", "feedback")


def get_agent_definitions(search_connection_id: str) -> dict:
    """Build agent definitions with built-in Azure AI Search tools.
    
    Args:
        search_connection_id: Foundry connection ID for Azure AI Search
        
    Returns:
        Dict mapping agent key to config (instructions, tools)
    """
    if not search_connection_id:
        raise ValueError(
            "search_connection_id required. Set AZURE_AI_SEARCH_CONNECTION_NAME in .env"
        )
    
    # Built-in Azure AI Search tool for resumes (semantic ranking)
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
    
    # Built-in Azure AI Search tool for feedback (semantic ranking)
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
    
    return {
        "orchestrator": orchestrator.get_config(),
        "profile": profile.get_config(),
        "search": search.get_config(resume_search_tool),
        "insights": insights.get_config(feedback_search_tool),
        "outreach": outreach.get_config(email_tool=SEND_EMAIL_TOOL),
    }


# List of all agent keys
AGENT_KEYS = ["orchestrator", "profile", "search", "insights", "outreach"]
