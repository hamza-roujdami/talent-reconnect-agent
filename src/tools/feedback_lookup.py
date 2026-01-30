"""Feedback history tools for InsightPulse agent."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from time import monotonic, sleep
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

load_dotenv()


class FeedbackConfigError(RuntimeError):
    """Raised when feedback search configuration is missing."""


def _get_env(*names: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    """Resolve the first populated environment variable in *names*."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    if required:
        joined = " or ".join(names)
        raise FeedbackConfigError(f"Missing {joined}. Update your .env.")
    return default


# Configuration from environment
SEARCH_ENDPOINT = _get_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT", required=True)
SEARCH_API_KEY = _get_env("SEARCH_SERVICE_API_KEY", "AZURE_SEARCH_API_KEY", "AZURE_SEARCH_KEY")
FEEDBACK_INDEX = _get_env("SEARCH_FEEDBACK_INDEX", "AZURE_FEEDBACK_INDEX_NAME", default="feedback")

_CLIENT: Optional[SearchClient] = None

# Caching
_CACHE_TTL_SECONDS = int(os.getenv("FEEDBACK_CACHE_TTL", "300"))
_CACHE_EMAIL: dict[str, tuple[float, Optional[dict]]] = {}
_CACHE_ID: dict[str, tuple[float, Optional[dict]]] = {}

# Recommendation scoring
RECOMMENDATION_BONUS = {"strong_hire": 15, "hire": 5, "maybe": 0, "no_hire": -15}

_FEEDBACK_FIELDS = [
    "id", "candidate_id", "candidate_email", "candidate_name",
    "interview_date", "interviewer", "role", "strengths",
    "concerns", "recommendation", "score", "notes",
]


def _get_client() -> SearchClient:
    """Get or create Azure AI Search client for feedback index."""
    global _CLIENT
    if _CLIENT is None:
        cred = AzureKeyCredential(SEARCH_API_KEY) if SEARCH_API_KEY else DefaultAzureCredential()
        _CLIENT = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=FEEDBACK_INDEX,
            credential=cred,
        )
    return _CLIENT


def _cache_get(cache: dict, key: str) -> Optional[dict]:
    """Return cached value if not expired."""
    entry = cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if monotonic() > expires_at:
        cache.pop(key, None)
        return None
    return value


def _cache_set(cache: dict, key: str, value: Optional[dict]) -> None:
    if _CACHE_TTL_SECONDS > 0:
        cache[key] = (monotonic() + _CACHE_TTL_SECONDS, value)


def _invalidate_cache(candidate_id: Optional[str] = None, candidate_email: Optional[str] = None) -> None:
    if candidate_email:
        _CACHE_EMAIL.pop(candidate_email, None)
    if candidate_id:
        _CACHE_ID.pop(candidate_id, None)


def _escape_filter_value(value: str) -> str:
    return value.replace("'", "''")


def _query_feedback(filter_expression: str) -> list:
    """Execute feedback query with retry logic."""
    client = _get_client()
    for attempt in range(3):
        try:
            results = client.search(
                search_text="*",
                filter=filter_expression,
                order_by=["interview_date desc"],
                select=_FEEDBACK_FIELDS,
            )
            return list(results)
        except Exception as exc:
            if attempt >= 2:
                raise FeedbackConfigError(f"Feedback query failed: {exc}") from exc
            sleep(0.5 * (2 ** attempt))
    return []


def _serialize_history(history: list, *, default_email: str = "", default_id: str = "") -> dict:
    """Convert raw search results to feedback history dict."""
    latest = history[0]
    payload = {
        "candidate_id": default_id or latest.get("candidate_id", ""),
        "candidate_email": default_email or latest.get("candidate_email", ""),
        "candidate_name": latest.get("candidate_name", "Unknown"),
        "total_interviews": len(history),
        "latest_interview": {
            "interview_date": latest.get("interview_date", ""),
            "interviewer": latest.get("interviewer", ""),
            "role": latest.get("role", ""),
            "strengths": latest.get("strengths", ""),
            "concerns": latest.get("concerns", ""),
            "recommendation": latest.get("recommendation", ""),
            "score": latest.get("score", 0),
            "notes": latest.get("notes", ""),
        },
        "all_interviews": [
            {
                "interview_date": e.get("interview_date", ""),
                "interviewer": e.get("interviewer", ""),
                "role": e.get("role", ""),
                "recommendation": e.get("recommendation", ""),
                "score": e.get("score", 0),
            }
            for e in history
        ],
    }
    recommendation = latest.get("recommendation", "")
    payload["has_red_flag"] = recommendation == "no_hire"
    payload["score_adjustment"] = RECOMMENDATION_BONUS.get(recommendation, 0)
    return payload


def get_feedback_history(candidate_email: str) -> Optional[dict]:
    """Get interview feedback history for a candidate by email."""
    cached = _cache_get(_CACHE_EMAIL, candidate_email)
    if cached is not None:
        return cached
    
    history = _query_feedback(f"candidate_email eq '{_escape_filter_value(candidate_email)}'")
    if not history:
        _cache_set(_CACHE_EMAIL, candidate_email, None)
        return None
    
    payload = _serialize_history(history, default_email=candidate_email)
    _cache_set(_CACHE_EMAIL, candidate_email, payload)
    return payload


def get_feedback_by_candidate_id(candidate_id: str) -> Optional[dict]:
    """Get interview feedback history for a candidate by ID."""
    cached = _cache_get(_CACHE_ID, candidate_id)
    if cached is not None:
        return cached
    
    history = _query_feedback(f"candidate_id eq '{_escape_filter_value(candidate_id)}'")
    if not history:
        _cache_set(_CACHE_ID, candidate_id, None)
        return None
    
    payload = _serialize_history(history, default_id=candidate_id)
    _cache_set(_CACHE_ID, candidate_id, payload)
    return payload


def format_feedback_summary(feedback: dict) -> str:
    """Format feedback history for display."""
    if not feedback:
        return "No previous interview history."
    
    latest = feedback["latest_interview"]
    interview_date = latest.get("interview_date", "")
    if interview_date:
        try:
            dt = datetime.fromisoformat(interview_date.replace("Z", "+00:00"))
            interview_date = dt.strftime("%Y-%m-%d")
        except:
            pass
    
    lines = [
        f"📋 **Interview History** ({feedback['total_interviews']} interview(s))",
        f"",
        f"**Latest Interview:** {interview_date}",
        f"**Role:** {latest['role']}",
        f"**Interviewer:** {latest['interviewer']}",
        f"**Score:** {latest['score']}/100",
        f"**Recommendation:** {latest['recommendation'].replace('_', ' ').title()}",
        f"",
        f"**Strengths:** {latest['strengths']}",
    ]
    
    if latest.get("concerns"):
        lines.append(f"**Concerns:** {latest['concerns']}")
    
    if feedback.get("has_red_flag"):
        lines.extend(["", "⚠️ **Red Flag:** Previous no-hire recommendation"])
    
    return "\n".join(lines)


# ============================================================================
# Tool functions for agents
# ============================================================================

def lookup_feedback_by_emails(candidate_emails: list[str]) -> str:
    """
    Fetch interview feedback history for candidates by email.
    
    Args:
        candidate_emails: List of candidate email addresses to look up
        
    Returns:
        Formatted feedback summary for each candidate with history
    """
    results = []
    candidates_with_history = 0
    red_flags = 0
    
    for email in candidate_emails:
        feedback = get_feedback_history(email)
        if feedback:
            candidates_with_history += 1
            if feedback.get("has_red_flag"):
                red_flags += 1
            results.append(f"**{email}**\n{format_feedback_summary(feedback)}")
    
    if not results:
        return "No interview history found for any of the candidates."
    
    header = f"📊 **Feedback History Summary**\n"
    header += f"Found history for {candidates_with_history}/{len(candidate_emails)} candidates"
    if red_flags:
        header += f" | ⚠️ {red_flags} red flag(s)\n"
    else:
        header += "\n"
    header += "=" * 50 + "\n\n"
    
    return header + "\n\n---\n\n".join(results)


def lookup_feedback_by_ids(candidate_ids: list[str]) -> str:
    """
    Fetch interview feedback history for candidates by ID.
    
    Args:
        candidate_ids: List of candidate IDs from search results
        
    Returns:
        Formatted feedback summary for each candidate with history
    """
    results = []
    candidates_with_history = 0
    red_flags = 0
    
    for cid in candidate_ids:
        feedback = get_feedback_by_candidate_id(cid)
        # Fallback: if the "id" is actually an email, try email lookup
        if not feedback and "@" in cid:
            feedback = get_feedback_history(cid)
        
        if feedback:
            candidates_with_history += 1
            name = feedback.get("candidate_name", cid)
            if feedback.get("has_red_flag"):
                red_flags += 1
            results.append(f"**{name}** ({cid})\n{format_feedback_summary(feedback)}")
    
    if not results:
        return "No interview history found for any of the candidates."
    
    header = f"📊 **Feedback History Summary**\n"
    header += f"Found history for {candidates_with_history}/{len(candidate_ids)} candidates"
    if red_flags:
        header += f" | ⚠️ {red_flags} red flag(s)\n"
    else:
        header += "\n"
    header += "=" * 50 + "\n\n"
    
    return header + "\n\n---\n\n".join(results)


def log_interview_feedback(
    candidate_id: str,
    candidate_email: str,
    candidate_name: str,
    interviewer: str,
    role: str,
    strengths: str,
    concerns: str,
    recommendation: str,
    score: int,
    notes: str = "",
) -> str:
    """
    Record new interview feedback for a candidate.
    
    Args:
        candidate_id: Candidate's ID from the resumes index
        candidate_email: Candidate's email address
        candidate_name: Candidate's full name
        interviewer: Name of the interviewer
        role: Role the candidate was interviewed for
        strengths: Observed strengths
        concerns: Any concerns or issues
        recommendation: One of: strong_hire, hire, maybe, no_hire
        score: Interview score from 0-100
        notes: Additional notes (optional)
        
    Returns:
        Confirmation message
    """
    if recommendation not in ["strong_hire", "hire", "maybe", "no_hire"]:
        return f"Invalid recommendation: {recommendation}. Use: strong_hire, hire, maybe, or no_hire"
    
    if not 0 <= score <= 100:
        return f"Invalid score: {score}. Must be between 0 and 100."
    
    client = _get_client()
    interview_date = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    
    feedback = {
        "id": str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "candidate_email": candidate_email,
        "candidate_name": candidate_name,
        "interview_date": interview_date,
        "interviewer": interviewer,
        "role": role,
        "strengths": strengths,
        "concerns": concerns,
        "recommendation": recommendation,
        "score": score,
        "notes": notes,
    }
    
    client.upload_documents(documents=[feedback])
    _invalidate_cache(candidate_id=candidate_id, candidate_email=candidate_email)
    
    return f"✅ Feedback recorded for {candidate_name} ({candidate_email}) - {recommendation.replace('_', ' ').title()}"
