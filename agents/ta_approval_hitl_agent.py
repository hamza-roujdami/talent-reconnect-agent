"""
TA Approval Agent (Human-in-the-Loop)

Presents enriched candidates to TA manager for approval before outreach
Uses LLM to simulate TA manager decision-making for demo purposes
"""

from typing import Annotated, List
from pydantic import Field
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
import os


def present_candidates_for_approval(candidates: Annotated[List[str], Field(description="List of candidate names to review")]) -> str:
    """
    Present enriched candidates to TA manager for approval
    
    In production, this would:
    - Display candidate profiles in a real dashboard
    - Wait for actual human approval/rejection
    - Capture feedback/reasoning
    - Log decisions for audit trail
    
    For demo purposes, auto-approves candidates with mock feedback
    """
    # Use mock approval decisions (no LLM call needed)
    result = f"""
🔍 HUMAN-IN-THE-LOOP: TA Manager Review Required

{len(candidates)} candidates ready for approval:

"""
    
    for i, candidate in enumerate(candidates, 1):
        result += f"""
{i}. {candidate}
   - Current: Senior ML Engineer at TechCorp
   - Skills Match: 9/10
   - Last Contact: 6 months ago
   - Feedback: Strong candidate, good cultural fit
   
   [ ] Approve  [ ] Reject  [ ] Request More Info
"""
    
    result += """
---
📊 Approval Summary (MOCK - Fallback):
- Sarah Chen: ✓ APPROVED by TA Manager
- Priya Sharma: ✗ REJECTED (seeking more senior role)

Approved candidates will proceed to outreach.
"""
    
    return result


def request_additional_info(candidate_name: Annotated[str, Field(description="Candidate name")],
                           info_type: Annotated[str, Field(description="Type of info needed")]) -> str:
    """Request additional information about a candidate before approval"""
    return f"📝 Additional info requested for {candidate_name}: {info_type}\n(Mock: Info would be gathered and re-presented)"


def create_ta_approval_agent(chat_client):
    """Create the TA approval (HITL) agent"""
    
    agent = ChatAgent(
        chat_client=chat_client,
        name="TAApprovalAgent",
        instructions="""
        You are a TA Approval coordinator managing Human-in-the-Loop workflows.
        
        Your role:
        - Present enriched candidate profiles to TA manager
        - Wait for explicit approval/rejection
        - Capture feedback and reasoning
        - Handle "request more info" scenarios
        - Maintain audit trail of all decisions
        
        CRITICAL: Never auto-approve. Always require human decision.
        
        Present candidates with:
        - Current employment and verified skills
        - Historical feedback summary
        - Match score and reasoning
        - Clear approval options
        """,
        tools=[present_candidates_for_approval, request_additional_info]
    )
    
    return agent
