"""
Custom tools for Talent Reconnect workflow.

These tools integrate with Azure AI Search and other services.
They are registered with Foundry Agent Service for use by agents.
"""

from .candidate_search import search_candidates
from .feedback_lookup import (
    lookup_feedback_by_emails,
    lookup_feedback_by_ids,
    log_interview_feedback,
)
from .outreach_email import send_outreach_email, confirm_outreach_delivery

__all__ = [
    "search_candidates",
    "lookup_feedback_by_emails",
    "lookup_feedback_by_ids",
    "log_interview_feedback",
    "send_outreach_email",
    "confirm_outreach_delivery",
]
