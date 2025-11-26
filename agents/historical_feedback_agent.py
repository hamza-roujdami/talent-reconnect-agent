"""
Historical Feedback Agent

Applies historical feedback from ATS/CRM to filter candidates
"""

from typing import Annotated, List
from pydantic import Field
from agent_framework import ChatAgent


def apply_historical_feedback(candidate_ids: Annotated[List[str], Field(description="List of candidate IDs or names")]) -> str:
    """
    Query ATS/CRM for historical feedback on candidates
    Filter out candidates with:
    - Previous rejections for similar roles
    - Opt-out preferences
    - Recent negative interactions
    """
    # Mock implementation - in production, query actual ATS/CRM API
    
    feedback_data = {
        "Sarah Chen": {
            "status": "✓ Eligible",
            "last_contact": "6 months ago",
            "previous_roles": "Applied to 2 positions, 1 interview",
            "feedback": "Strong candidate, good cultural fit",
            "opt_out": False
        },
        "Marcus Johnson": {
            "status": "⚠️ Recently Contacted",
            "last_contact": "2 weeks ago",
            "previous_roles": "Just applied to ML Lead position",
            "feedback": "Active in pipeline, avoid duplicate outreach",
            "opt_out": False
        },
        "Priya Sharma": {
            "status": "✓ Eligible",
            "last_contact": "1 year ago",
            "previous_roles": "Interviewed for Data Science role",
            "feedback": "Positive interview, open to new opportunities",
            "opt_out": False
        }
    }
    
    result = """
✓ Historical Feedback Analysis Complete

Candidate Feedback Summary:
"""
    
    filtered_candidates = []
    
    for name, feedback in feedback_data.items():
        result += f"""
{name}:
  Status: {feedback['status']}
  Last Contact: {feedback['last_contact']}
  History: {feedback['previous_roles']}
  Notes: {feedback['feedback']}
"""
        
        if feedback['status'] == "✓ Eligible":
            filtered_candidates.append(name)
    
    result += f"""
Recommendation: Proceed with {len(filtered_candidates)} candidates: {', '.join(filtered_candidates)}
Filter reason: Marcus Johnson recently contacted (avoid duplicate outreach)
"""
    
    return result


def create_historical_feedback_agent(chat_client):
    """Create the historical feedback agent"""
    
    agent = ChatAgent(
        chat_client=chat_client,
        name="HistoricalFeedbackAgent",
        instructions="""
        You are a Historical Feedback specialist for ATS/CRM integration.
        
        Your role:
        - Query ATS/CRM for candidate interaction history
        - Filter out recently contacted candidates
        - Respect opt-out preferences
        - Apply rejection feedback (similar roles, timing)
        - Flag candidates with negative experiences
        
        Ensure compliance with candidate preferences and timing rules.
        """,
        tools=[apply_historical_feedback]
    )
    
    return agent
