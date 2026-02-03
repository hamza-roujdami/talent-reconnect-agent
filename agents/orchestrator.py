"""Orchestrator Agent - TalentHub.

Routes user requests to the appropriate specialist agent.
"""

INSTRUCTIONS = """You are TalentHub, the recruiting assistant coordinator.

Your role is to route user requests to the right specialist and provide a cohesive experience.

Specialists available:
- RoleCrafter (profile): Define job requirements and candidate profiles
- TalentScout (search): Find candidates in the resume database  
- InsightPulse (insights): Get interview feedback and candidate history
- ConnectPilot (outreach): Draft personalized outreach emails

Guide the conversation naturally. When the user's intent is clear, tell them which specialist will help and what to expect."""


def get_config() -> dict:
    """Return orchestrator agent configuration."""
    return {
        "instructions": INSTRUCTIONS,
        "tools": [],
    }


def route(message: str) -> str:
    """Simple keyword routing to determine target agent.
    
    Args:
        message: User message to route
        
    Returns:
        Agent key (orchestrator, search, insights, outreach, profile)
    """
    msg = message.lower()
    
    # Search: explicit search intent
    if any(w in msg for w in ["search", "find candidates", "look for candidates", "who has", "show me candidates"]):
        return "search"
    # Insights: feedback and interview history
    if any(w in msg for w in ["feedback", "interview", "history", "insights", "scored", "performance"]):
        return "insights"
    # Outreach: contacting candidates
    if any(w in msg for w in ["email", "outreach", "contact", "reach out", "message", "send"]):
        return "outreach"
    # Profile: hiring intent - catches job titles and hiring language
    if any(w in msg for w in [
        "role", "job", "requirements", "profile", "define", "hiring", "hire",
        "looking for", "need a", "need an", "want to hire", "recruit",
        "engineer", "manager", "developer", "designer", "analyst", "scientist",
        "architect", "lead", "director", "specialist", "consultant",
    ]):
        return "profile"
    
    return "orchestrator"
