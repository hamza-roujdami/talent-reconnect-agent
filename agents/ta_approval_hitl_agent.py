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
    Uses LLM to simulate approval decisions for demo
    
    In production, this would:
    - Display candidate profiles in a real dashboard
    - Wait for actual human approval/rejection
    - Capture feedback/reasoning
    - Log decisions for audit trail
    """
    try:
        from openai import AzureOpenAI
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )
        
        client = AzureOpenAI(
            azure_endpoint=os.getenv("OPENAI_API_BASE"),
            azure_ad_token_provider=token_provider,
            api_version="2024-10-21"
        )
        
        prompt = f"""Review these candidates for a Senior Machine Learning Engineer position:

Candidates to review:
{chr(10).join(f'- {c}' for c in candidates)}

Candidate details:
- Sarah Chen: Senior ML Engineer at TechCorp, 8 years exp, 9/10 skills match, last contact 6 months ago
- Priya Sharma: AI Research Engineer at DataFlow, 5 years exp, 7/10 skills match, positive interview history

For each candidate, make a realistic approval decision based on:
- Skills match and experience
- Cultural fit indicators
- Historical feedback

Format your response as:
Candidate Name: ✓ APPROVED or ✗ REJECTED
Reason: [brief explanation]

Be realistic and professional."""
        
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
            messages=[
                {"role": "system", "content": "You are a TA Manager reviewing candidates for approval. Make realistic decisions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        approval_decisions = response.choices[0].message.content
        
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
        
        result += f"""
---
📊 Approval Decisions (LLM-Simulated for Demo):

{approval_decisions}

Note: In production, this would be actual human approval via dashboard.
Approved candidates will proceed to outreach.
"""
        
        return result
        
    except Exception as e:
        print(f"⚠️ LLM approval simulation failed, using fallback: {e}")
        # Fallback to mock decisions
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
