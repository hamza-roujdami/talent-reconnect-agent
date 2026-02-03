"""Tool implementations for Talent Reconnect agents.

Note: Search and feedback use built-in AzureAISearchAgentTool.
Only email tool is used directly via FunctionTool.
"""

from .email import send_outreach_email

__all__ = ["send_outreach_email"]
