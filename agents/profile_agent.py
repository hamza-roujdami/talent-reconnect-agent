"""
RoleCrafter (Profile Agent) - Generates ideal candidate profiles from job descriptions.

Takes a job description or requirements and produces:
- Structured ideal candidate profile
- Search-optimized query
- Filter parameters
"""
from agent_framework import ChatAgent
from typing import Optional

PROFILE_AGENT_NAME = "RoleCrafter"


def create_profile_agent(
    chat_client,
    *,
    middleware: Optional[list] = None,
    function_middleware: Optional[list] = None,
) -> ChatAgent:
    """Create the Profile Agent.
    
    This agent:
    1. Parses job requirements from user input
    2. Generates an "ideal candidate" profile
    3. Creates search-optimized queries and filters
    
    Args:
        chat_client: The chat client to use
        middleware: Agent-level middleware for logging/monitoring
        function_middleware: Function-level middleware for tool calls
    """
    # Combine middleware lists for new API
    all_middleware = []
    if middleware:
        all_middleware.extend(middleware)
    if function_middleware:
        all_middleware.extend(function_middleware)
    
    return chat_client.as_agent(
        name=PROFILE_AGENT_NAME,
        default_options={"temperature": 0.3},
        middleware=all_middleware or None,
        instructions="""You are a recruiting profile specialist. Turn hiring manager requests into polished, recruiter-ready job briefs that a TA can paste into a posting.

Always respond with this structure EXACTLY ONCE:

---

🎯 **Role Snapshot**
- **Title:** [Clear job title]
- **Seniority:** [Level]
- **Location:** [City/Country or Remote]
- **Experience:** [X-Y years]
- **Work Style:** [On-site / Hybrid / Remote]

📝 **Job Pitch**
One warm paragraph (2 sentences max) that sells the opportunity to a candidate.

🛠️ **Key Responsibilities**
- Bullet 1
- Bullet 2
- Bullet 3 (only 3-4 bullets, action-oriented)

🧰 **Must-Have Skills**
- Skill 1 — short qualifier
- Skill 2 — short qualifier
- Skill 3 — short qualifier (3-5 bullets max)

✨ **Nice-to-Haves**
- Bonus 1
- Bonus 2 (2-4 concise bullets)

🤝 **Team & Process**
One sentence about team size, culture, or why the hire matters.

✅ **Next Step**
Say **yes** to start the search, or tell me what to tweak.

---

Tone rules:
- Sounds conversational and recruiter-friendly (no rigid template language)
- Replace placeholders with real values (never leave brackets)
- Mention company/domain if provided; otherwise keep it neutral
- Keep the entire brief under 180 words
""",
    )
