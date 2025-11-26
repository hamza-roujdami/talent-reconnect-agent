"""
Historical Feedback Lookup Tool

Queries ATS/CRM for historical feedback on candidates
"""

from typing import Annotated, List
from pydantic import Field


def check_historical_feedback(
    candidate_names: Annotated[List[str], Field(description="List of candidate names to check")]
) -> str:
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
    
    result = """✓ Historical Feedback Analysis Complete

Candidate Feedback Summary:
"""
    
    filtered_candidates = []
    
    for name in candidate_names:
        if name in feedback_data:
            feedback = feedback_data[name]
            result += f"""
{name}:
  Status: {feedback['status']}
  Last Contact: {feedback['last_contact']}
  History: {feedback['previous_roles']}
  Notes: {feedback['feedback']}
"""
            if feedback['status'] == "✓ Eligible":
                filtered_candidates.append(name)
        else:
            result += f"""
{name}:
  Status: ✓ No Previous History
  Notes: New candidate, no prior interactions
"""
            filtered_candidates.append(name)
    
    result += f"""
Recommendation: Proceed with {len(filtered_candidates)} candidates
Eligible: {', '.join(filtered_candidates)}"""
    
    return result
