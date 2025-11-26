"""
Profile Enrichment Agent

Enriches candidate profiles with current employment data via compliant APIs
"""

from typing import Annotated, List
from pydantic import Field
from agent_framework import ChatAgent


def enrich_candidate_profile(candidate_name: Annotated[str, Field(description="Candidate name")],
                             candidate_email: Annotated[str, Field(description="Candidate email")]) -> str:
    """
    Enrich candidate profile with current employment data
    Uses compliant profile enrichment API (respects GDPR, opt-outs)
    """
    # Mock implementation - in production, use compliant data provider API
    
    enrichment_data = {
        "Sarah Chen": {
            "current_company": "TechCorp Solutions",
            "current_title": "Senior ML Engineer",
            "tenure": "2.5 years",
            "location": "San Francisco, CA",
            "skills_verified": ["Python", "TensorFlow", "Azure ML", "MLOps"],
            "linkedin_url": "linkedin.com/in/sarahchen",
            "open_to_opportunities": True
        },
        "Priya Sharma": {
            "current_company": "DataFlow Analytics",
            "current_title": "AI Research Engineer",
            "tenure": "1.8 years",
            "location": "Austin, TX",
            "skills_verified": ["PyTorch", "NLP", "Azure", "Docker"],
            "linkedin_url": "linkedin.com/in/priyasharma",
            "open_to_opportunities": True
        }
    }
    
    if candidate_name in enrichment_data:
        data = enrichment_data[candidate_name]
        return f"""
✓ Profile Enriched: {candidate_name}

Current Employment:
  Company: {data['current_company']}
  Title: {data['current_title']}
  Tenure: {data['tenure']}
  Location: {data['location']}

Verified Skills: {', '.join(data['skills_verified'])}
LinkedIn: {data['linkedin_url']}
Open to Opportunities: {'✓ Yes' if data['open_to_opportunities'] else '✗ No'}
"""
    else:
        return f"⚠️ Limited enrichment data available for {candidate_name}"


def create_profile_enricher_agent(chat_client):
    """Create the profile enrichment agent"""
    
    agent = ChatAgent(
        chat_client=chat_client,
        name="ProfileEnrichmentAgent",
        instructions="""
        You are a Profile Enrichment specialist using compliant data APIs.
        
        Your role:
        - Enrich candidate profiles with current employment
        - Verify current company, title, tenure
        - Add LinkedIn and professional network data
        - Check "open to opportunities" signals
        - Ensure GDPR/privacy compliance
        
        Only use compliant, consent-based data sources.
        """,
        tools=[enrich_candidate_profile]
    )
    
    return agent
