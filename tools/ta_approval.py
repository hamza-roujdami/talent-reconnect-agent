"""
TA Approval Tool (Human-in-the-Loop)

Presents candidates for TA manager approval
"""

import os
from typing import Annotated, List
from pydantic import Field
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI


def request_ta_approval(
    candidate_names: Annotated[List[str], Field(description="List of candidate names to review for approval")]
) -> str:
    """
    Present enriched candidates to TA manager for approval
    
    In production, this would:
    - Display candidate profiles in a dashboard
    - Wait for actual human approval/rejection
    - Capture feedback/reasoning
    - Log decisions for audit trail
    
    For demo: Uses LLM to simulate approval decisions
    """
    try:
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
{chr(10).join(f'- {c}' for c in candidate_names)}

Candidate details:
- Sarah Chen: Senior ML Engineer at TechCorp, 8 years exp, 9/10 skills match, last contact 6 months ago
- Priya Sharma: AI Research Engineer at DataFlow, 5 years exp, 7/10 skills match, positive interview history

For each candidate, make a realistic approval decision based on:
- Skills match and experience
- Cultural fit indicators
- Historical feedback

Format your response as:
✅ APPROVED: Candidate Name - Reason
or
❌ REJECTED: Candidate Name - Reason"""

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-deployment"),
            messages=[
                {"role": "system", "content": "You are a TA manager reviewing candidates for approval."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        decision = response.choices[0].message.content
        
        return f"""✓ TA Approval Review Complete

Candidates Reviewed: {len(candidate_names)}

Decisions:
{decision}

Next Step: Proceed with approved candidates for outreach"""
        
    except Exception as e:
        # Fallback to simple approval for demo
        approved = candidate_names[:2] if len(candidate_names) >= 2 else candidate_names
        
        result = f"""✓ TA Approval Review Complete (Simulated)

Candidates Reviewed: {len(candidate_names)}

Decisions:
"""
        for name in candidate_names:
            if name in approved:
                result += f"✅ APPROVED: {name} - Strong skills match and positive history\n"
            else:
                result += f"❌ REJECTED: {name} - Recently contacted, avoid duplicate outreach\n"
        
        result += f"\nApproved: {len(approved)} candidates"
        return result
