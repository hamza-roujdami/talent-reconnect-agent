"""Feedback history helpers backed by Azure AI Search."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from time import monotonic, sleep
from typing import Optional

from agent_framework.azure import AzureAISearchContextProvider
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

# Ensure local .env-style files are honored just like the resume search setup.
for env_file in (".env", ".env.local", ".emv"):
    load_dotenv(env_file, override=False)


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
        raise FeedbackConfigError(
            f"Missing {joined}. Update your .env with the Azure AI Search settings."
        )

    return default


SEARCH_ENDPOINT = _get_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT", required=True)
SEARCH_API_KEY = _get_env("SEARCH_SERVICE_API_KEY", "AZURE_SEARCH_API_KEY", "AZURE_SEARCH_KEY")
FEEDBACK_INDEX = _get_env(
    "SEARCH_FEEDBACK_INDEX",
    "AZURE_FEEDBACK_INDEX_NAME",
    "AZURE_FEEDBACK_INDEX",
    default="feedback",
)


if SEARCH_API_KEY:
    _SEARCH_CREDENTIAL = AzureKeyCredential(SEARCH_API_KEY)
else:
    _SEARCH_CREDENTIAL = DefaultAzureCredential()


_CLIENT: Optional[SearchClient] = None


def _get_client() -> SearchClient:
    """Build (and memoize) the Azure AI Search client for the feedback index."""

    global _CLIENT

    if not SEARCH_ENDPOINT or not FEEDBACK_INDEX:
        raise FeedbackConfigError("Azure AI Search feedback index is not configured.")

    if _CLIENT is None:
        _CLIENT = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=FEEDBACK_INDEX,
            credential=_SEARCH_CREDENTIAL,
        )

        # Register atexit to close the client on interpreter shutdown
        import atexit
        def _close_feedback_client() -> None:
            global _CLIENT
            if _CLIENT is not None:
                try:
                    _CLIENT.close()
                except Exception:
                    pass
        atexit.register(_close_feedback_client)

    return _CLIENT


def build_feedback_context_provider(
    *,
    mode: Optional[str] = None,
    top_k: Optional[int] = None,
    knowledge_base_name: Optional[str] = None,
    output_mode: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
) -> AzureAISearchContextProvider:
    """Create an AzureAISearchContextProvider configured for the feedback index."""

    resolved_mode = (mode or os.getenv("AZURE_FEEDBACK_MODE") or "agentic").lower()
    if os.getenv("AZURE_FEEDBACK_REQUIRE_AGENTIC", "").lower() == "true" and resolved_mode != "agentic":
        raise FeedbackConfigError("AZURE_FEEDBACK_REQUIRE_AGENTIC is set but resolved mode is not agentic.")
    resolved_top_k = top_k or int(os.getenv("AZURE_FEEDBACK_TOP_K", os.getenv("AZURE_SEARCH_TOP_K", "4")))
    resolved_output_mode = output_mode or os.getenv(
        "AZURE_FEEDBACK_KB_OUTPUT_MODE",
        os.getenv("AZURE_SEARCH_KB_OUTPUT_MODE", "extractive_data"),
    )
    resolved_reasoning = reasoning_effort or os.getenv(
        "AZURE_FEEDBACK_RETRIEVAL_REASONING",
        os.getenv("AZURE_SEARCH_RETRIEVAL_REASONING", "minimal"),
    )
    kb_name = knowledge_base_name or _get_env(
        "SEARCH_FEEDBACK_KNOWLEDGE_BASE_NAME",
        "AZURE_FEEDBACK_KNOWLEDGE_BASE_NAME",
        "AZURE_SEARCH_KNOWLEDGE_BASE_NAME",
    )

    credential = None if SEARCH_API_KEY else DefaultAzureCredential()
    kwargs: dict = {
        "endpoint": SEARCH_ENDPOINT,
        "api_key": SEARCH_API_KEY,
        "credential": credential,
    }

    if resolved_mode == "agentic":
        kwargs.update(
            {
                "mode": "agentic",
                "knowledge_base_output_mode": resolved_output_mode,
                "retrieval_reasoning_effort": resolved_reasoning,
            }
        )

        if kb_name:
            kwargs["knowledge_base_name"] = kb_name
        else:
            resource_url = _get_env(
                "FOUNDRY_CHAT_ENDPOINT",
                "AZURE_OPENAI_RESOURCE_URL",
                "AZURE_OPENAI_ENDPOINT",
                required=True,
            )
            model_deployment = _get_env(
                "FOUNDRY_MODEL_FAST",
                "FOUNDRY_MODEL_PRIMARY",
                "AZURE_AI_MODEL_DEPLOYMENT_NAME",
                "AZURE_OPENAI_AGENTIC_DEPLOYMENT",
                "AZURE_OPENAI_DEPLOYMENT",
                default="gpt-4o-mini",
            )
            kwargs.update(
                {
                    "index_name": FEEDBACK_INDEX,
                    "azure_openai_resource_url": resource_url,
                    "model_deployment_name": model_deployment,
                    "top_k": resolved_top_k,
                }
            )
    else:
        semantic_config = _get_env(
            "SEARCH_FEEDBACK_SEMANTIC_CONFIG",
            "AZURE_FEEDBACK_SEMANTIC_CONFIG",
            "AZURE_SEARCH_SEMANTIC_CONFIG",
            default="default",
        )
        kwargs.update(
            {
                "mode": "semantic",
                "index_name": FEEDBACK_INDEX,
                "semantic_configuration_name": semantic_config,
                "top_k": resolved_top_k,
            }
        )

    return AzureAISearchContextProvider(**kwargs)


# Recommendation to score adjustment
RECOMMENDATION_BONUS = {
    "strong_hire": 15,
    "hire": 5,
    "maybe": 0,
    "no_hire": -15,
}


_FEEDBACK_FIELDS = [
    "id",
    "candidate_id",
    "candidate_email",
    "candidate_name",
    "interview_date",
    "interviewer",
    "role",
    "strengths",
    "concerns",
    "recommendation",
    "score",
    "notes",
]


# Lightweight in-memory caches for feedback lookups
_CACHE_TTL_SECONDS = int(os.getenv("FEEDBACK_CACHE_TTL", os.getenv("AZURE_SEARCH_CACHE_TTL", "300")))
_CACHE_EMAIL: dict[str, tuple[float, Optional[dict]]] = {}
_CACHE_ID: dict[str, tuple[float, Optional[dict]]] = {}

# Retry/backoff settings for Azure AI Search calls
_SEARCH_RETRY_ATTEMPTS = int(os.getenv("FEEDBACK_SEARCH_RETRY_ATTEMPTS", os.getenv("AZURE_SEARCH_RETRY_ATTEMPTS", "3")))
_SEARCH_RETRY_BACKOFF = float(os.getenv("FEEDBACK_SEARCH_RETRY_BACKOFF", os.getenv("AZURE_SEARCH_RETRY_BACKOFF", "0.5")))
_SEARCH_TIMEOUT = float(os.getenv("FEEDBACK_SEARCH_TIMEOUT_SECONDS", os.getenv("AZURE_SEARCH_TIMEOUT_SECONDS", "10")))


def _escape_filter_value(value: str) -> str:
    return value.replace("'", "''")


def _cache_get(cache: dict[str, tuple[float, Optional[dict]]], key: str) -> Optional[dict]:
    """Return cached value if not expired."""

    entry = cache.get(key)
    if not entry:
        return None

    expires_at, value = entry
    if monotonic() > expires_at:
        cache.pop(key, None)
        return None
    return value


def _cache_set(cache: dict[str, tuple[float, Optional[dict]]], key: str, value: Optional[dict]) -> None:
    if _CACHE_TTL_SECONDS <= 0:
        return
    cache[key] = (monotonic() + _CACHE_TTL_SECONDS, value)


def _invalidate_cache(candidate_id: Optional[str] = None, candidate_email: Optional[str] = None) -> None:
    if candidate_email:
        _CACHE_EMAIL.pop(candidate_email, None)
    if candidate_id:
        _CACHE_ID.pop(candidate_id, None)


def _query_feedback(filter_expression: str):
    client = _get_client()
    last_exc = None

    for attempt in range(_SEARCH_RETRY_ATTEMPTS):
        try:
            results = client.search(
                search_text="*",
                filter=filter_expression,
                order_by=["interview_date desc"],
                select=_FEEDBACK_FIELDS,
                timeout=_SEARCH_TIMEOUT,
            )
            return list(results)
        except FeedbackConfigError:
            raise
        except Exception as exc:  # pragma: no cover - surfaced to the agent as a tool failure
            last_exc = exc
            if attempt + 1 >= _SEARCH_RETRY_ATTEMPTS:
                break
            sleep(_SEARCH_RETRY_BACKOFF * (2**attempt))

    raise FeedbackConfigError(f"Azure AI Search query failed after retries: {last_exc}") from last_exc


def _serialize_history(history, *, default_email: Optional[str] = None, default_id: Optional[str] = None) -> dict:
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
                "interview_date": entry.get("interview_date", ""),
                "interviewer": entry.get("interviewer", ""),
                "role": entry.get("role", ""),
                "strengths": entry.get("strengths", ""),
                "concerns": entry.get("concerns", ""),
                "recommendation": entry.get("recommendation", ""),
                "score": entry.get("score", 0),
            }
            for entry in history
        ],
    }

    recommendation = latest.get("recommendation", "")
    payload["has_red_flag"] = recommendation == "no_hire"
    payload["score_adjustment"] = RECOMMENDATION_BONUS.get(recommendation, 0)

    return payload


def get_feedback_history(candidate_email: str) -> Optional[dict]:
    """Get interview feedback history for a candidate from Azure AI Search.
    
    Args:
        candidate_email: Email address of the candidate
        
    Returns:
        Dict with feedback history or None if no history
    """
    cached = _cache_get(_CACHE_EMAIL, candidate_email)
    if cached is not None:
        return cached

    try:
        history = _query_feedback(
            f"candidate_email eq '{_escape_filter_value(candidate_email)}'"
        )
    except FeedbackConfigError:
        raise

    if not history:
        _cache_set(_CACHE_EMAIL, candidate_email, None)
        return None

    payload = _serialize_history(history, default_email=candidate_email)
    _cache_set(_CACHE_EMAIL, candidate_email, payload)
    return payload


def get_feedback_by_candidate_id(candidate_id: str) -> Optional[dict]:
    """Get feedback by candidate_id (links to resume index).
    
    Args:
        candidate_id: The candidate's ID from the resumes index
        
    Returns:
        Dict with feedback history or None
    """
    cached = _cache_get(_CACHE_ID, candidate_id)
    if cached is not None:
        return cached

    try:
        history = _query_feedback(
            f"candidate_id eq '{_escape_filter_value(candidate_id)}'"
        )
    except FeedbackConfigError:
        raise

    if not history:
        _cache_set(_CACHE_ID, candidate_id, None)
        return None

    payload = _serialize_history(history, default_id=candidate_id)
    _cache_set(_CACHE_ID, candidate_id, payload)
    return payload


def get_batch_feedback(candidate_emails: list[str]) -> dict[str, Optional[dict]]:
    """Get feedback history for multiple candidates at once.
    
    Args:
        candidate_emails: List of email addresses
        
    Returns:
        Dict mapping email to feedback history (or None)
    """
    return {email: get_feedback_history(email) for email in candidate_emails}


def add_feedback(
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
) -> dict:
    """Add new interview feedback for a candidate to Azure AI Search.
    
    Args:
        candidate_id: ID linking to resumes index
        candidate_email: Candidate's email
        candidate_name: Candidate's full name
        interviewer: Name of interviewer
        role: Role being interviewed for
        strengths: Candidate strengths observed
        concerns: Any concerns or red flags
        recommendation: One of: strong_hire, hire, maybe, no_hire
        score: Interview score (0-100)
        notes: Additional notes
        
    Returns:
        The created feedback record
    """
    import uuid

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

    # Invalidate caches so subsequent reads see the latest write
    _invalidate_cache(candidate_id=candidate_id, candidate_email=candidate_email)

    return feedback


def format_feedback_summary(feedback: dict) -> str:
    """Format feedback history for display.
    
    Args:
        feedback: Feedback dict from get_feedback_history
        
    Returns:
        Formatted string for display
    """
    if not feedback:
        return "No previous interview history."
    
    latest = feedback["latest_interview"]
    
    # Format date nicely
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
        lines.append(f"")
        lines.append(f"⚠️ **Red Flag:** Previous no-hire recommendation")
    
    return "\n".join(lines)
