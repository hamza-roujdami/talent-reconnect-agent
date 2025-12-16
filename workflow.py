"""
Workflow - Single Agent with Tools

Simple workflow: One Recruiter agent that orchestrates the sequential process.
The agent has tools and follows instructions to pause for user approval.

Search modes:
- bm25: Fast keyword matching
- semantic: Neural reranking (+15-25% relevance, default)
"""
from agents.factory import create_recruiter, SearchMode


def create_workflow(search_mode: SearchMode = "semantic"):
    """Create the recruiting workflow.
    
    Args:
        search_mode: Which search backend to use:
            - "bm25": Fast keyword matching
            - "semantic": Neural reranking (+15-25%, default)
    
    Returns a single Recruiter agent with all tools.
    The agent follows a sequential HITL process:
    1. Understand requirements
    2. Generate JD (pause for approval)
    3. Search candidates (pause for selection)
    4. Draft outreach (pause for approval)
    """
    return create_recruiter(search_mode=search_mode)

