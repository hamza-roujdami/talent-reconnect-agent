"""Tool implementations for Talent Reconnect agents.

These tools connect to Azure AI Search to provide real data.
"""

from .search import search_candidates
from .feedback import lookup_feedback

__all__ = ["search_candidates", "lookup_feedback"]
