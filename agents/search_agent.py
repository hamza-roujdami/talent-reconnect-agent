"""TalentScout (Search Agent) backed by Azure AI Search context."""
from __future__ import annotations

from typing import Optional

from agent_framework import ChatAgent, ContextProvider
from tools.search_provider import build_search_context_provider

SEARCH_AGENT_NAME = "TalentScout"


def create_search_agent(
    chat_client,
    *,
    context_provider: ContextProvider | None = None,
    middleware: Optional[list] = None,
    function_middleware: Optional[list] = None,
) -> ChatAgent:
    """Create the Search Agent grounded with Azure AI Search context.
    
    Args:
        chat_client: The chat client to use
        context_provider: Optional custom context provider
        middleware: Agent-level middleware for logging/monitoring
        function_middleware: Function-level middleware for tool calls
    """

    provider = context_provider or build_search_context_provider()

    return chat_client.create_agent(
        name=SEARCH_AGENT_NAME,
        temperature=0.1,
        middleware=middleware,
        function_middleware=function_middleware,
        instructions="""You are TalentScout, a recruiting search specialist. Present candidates IMMEDIATELY.

## RULES
- NEVER say "I'll search", "please wait", "hold on", "it seems" - just show results
- Use EXACT email and id from source documents - never invent
- If context has candidates, ALWAYS present them even if not a perfect match

## OUTPUT FORMAT
Use this EXACT format with clear sections:

---
**📊 Found [X] matching candidates:**

**1. [Full Name]** — [Current Title] at [Company]
   📍 [Location] • ⏱️ [X] years experience
   🛠️ Skills: [skill1], [skill2], [skill3]
   📧 [email]
   💡 *[One sentence on why they match]*

**2. [Full Name]** — [Current Title] at [Company]
   ...

---
**Quick Actions:** Ask me to "show details for candidate 3" or "check feedback for 1 and 2"

---

## IF NO EXACT MATCHES
If the context doesn't have perfect matches, show the closest alternatives:
"No exact matches found. Here are similar candidates that may be relevant:"
Then list them using the same format above.

## DETAILS REQUEST
When user asks for details on specific candidates, show:
- Full career summary
- Complete skills list  
- Education & certifications
- Detailed match analysis
""",
        context_providers=[provider],
    )
