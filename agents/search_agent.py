"""TalentScout (Search Agent) backed by Azure AI Search context."""
from __future__ import annotations

from agent_framework import ChatAgent, ContextProvider
from tools.search_provider import build_search_context_provider

SEARCH_AGENT_NAME = "TalentScout"


def create_search_agent(
    chat_client,
    *,
    context_provider: ContextProvider | None = None,
) -> ChatAgent:
    """Create the Search Agent grounded with Azure AI Search context."""

    provider = context_provider or build_search_context_provider()

    return chat_client.create_agent(
        name=SEARCH_AGENT_NAME,
        temperature=0.1,
        instructions="""You are a recruiting search specialist.

Use the Azure AI Search context to surface highly relevant candidates and cite
sources in `[doc-id†source]` format. Present results as a numbered list (1., 2.,
3., …) so the recruiter can reference them later.

## Rules
1. When the user asks to "search", "find", or "refresh" candidates, describe
   a new ranked list grounded entirely in the provided context.
2. When they ask for details about candidate numbers you already shared, reuse
   that context—do not invent new people unless the user explicitly requests
   another search.
3. Highlight why each candidate matches (skills, years, location) and include
   1‑sentence summaries.
4. If the context does not contain an answer, say so and ask for clarifications
   instead of guessing.
""",
        context_providers=[provider],
    )
