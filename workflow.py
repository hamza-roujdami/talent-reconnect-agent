"""
Workflow - Single Agent with Tools

Simple workflow: One Recruiter agent that orchestrates the sequential process.
The agent has tools and follows instructions to pause for user approval.
"""
from agents.factory import create_recruiter


def create_workflow():
    """Create the recruiting workflow.
    
    Returns a single Recruiter agent with all tools.
    The agent follows a sequential HITL process:
    1. Understand requirements
    2. Generate JD (pause for approval)
    3. Search candidates (pause for selection)
    4. Draft outreach (pause for approval)
    """
    return create_recruiter()

