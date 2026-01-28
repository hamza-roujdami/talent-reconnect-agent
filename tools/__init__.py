"""Tools for Talent Reconnect agents.

Main tools used by multi-agent workflow:
- candidate_search: TalentScout uses this to search resumes
- feedback_lookup: InsightPulse uses this for interview feedback
- outreach_email: ConnectPilot uses this to send emails
"""
from tools.candidate_search import search_candidates
from tools.feedback_lookup import (
    get_feedback_history,
    get_feedback_by_candidate_id,
    add_feedback,
)
from tools.outreach_email import send_outreach_email, confirm_outreach_delivery

__all__ = [
    # Main tools
    "search_candidates",
    "get_feedback_history",
    "get_feedback_by_candidate_id",
    "add_feedback",
    "send_outreach_email",
    "confirm_outreach_delivery",
]
