"""
Feedback History Tools - Azure AI Search implementation.

Stores and retrieves interview feedback from Azure AI Search 'feedback' index.
Links to candidates via candidate_id or email.

Index: feedback
Fields: id, candidate_id, candidate_email, candidate_name, interview_date,
        interviewer, role, strengths, concerns, recommendation, score, notes
"""
import os
from typing import Optional
from datetime import datetime

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# Azure AI Search configuration
SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY", "")
FEEDBACK_INDEX = "feedback"

# Recommendation to score adjustment
RECOMMENDATION_BONUS = {
    "strong_hire": 15,
    "hire": 5,
    "maybe": 0,
    "no_hire": -15,
}


def _get_client() -> SearchClient:
    """Get Azure AI Search client for feedback index."""
    return SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=FEEDBACK_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY),
    )


def get_feedback_history(candidate_email: str) -> Optional[dict]:
    """Get interview feedback history for a candidate from Azure AI Search.
    
    Args:
        candidate_email: Email address of the candidate
        
    Returns:
        Dict with feedback history or None if no history
    """
    try:
        client = _get_client()
        
        # Search for feedback by email
        results = client.search(
            search_text="*",
            filter=f"candidate_email eq '{candidate_email}'",
            order_by=["interview_date desc"],
            select=["id", "candidate_id", "candidate_email", "candidate_name",
                    "interview_date", "interviewer", "role", "strengths",
                    "concerns", "recommendation", "score", "notes"],
        )
        
        history = list(results)
        
        if not history:
            return None
        
        # Get the most recent interview
        latest = history[0]
        
        return {
            "candidate_email": candidate_email,
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
                    "interview_date": h.get("interview_date", ""),
                    "interviewer": h.get("interviewer", ""),
                    "role": h.get("role", ""),
                    "strengths": h.get("strengths", ""),
                    "concerns": h.get("concerns", ""),
                    "recommendation": h.get("recommendation", ""),
                    "score": h.get("score", 0),
                }
                for h in history
            ],
            "has_red_flag": latest.get("recommendation") == "no_hire",
            "score_adjustment": RECOMMENDATION_BONUS.get(
                latest.get("recommendation", ""), 0
            ),
        }
    except Exception as e:
        print(f"Error fetching feedback: {e}")
        return None


def get_feedback_by_candidate_id(candidate_id: str) -> Optional[dict]:
    """Get feedback by candidate_id (links to resume index).
    
    Args:
        candidate_id: The candidate's ID from the resumes index
        
    Returns:
        Dict with feedback history or None
    """
    try:
        client = _get_client()
        
        results = client.search(
            search_text="*",
            filter=f"candidate_id eq '{candidate_id}'",
            order_by=["interview_date desc"],
        )
        
        history = list(results)
        
        if not history:
            return None
        
        latest = history[0]
        
        return {
            "candidate_id": candidate_id,
            "candidate_email": latest.get("candidate_email", ""),
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
            },
            "has_red_flag": latest.get("recommendation") == "no_hire",
            "score_adjustment": RECOMMENDATION_BONUS.get(
                latest.get("recommendation", ""), 0
            ),
        }
    except Exception as e:
        print(f"Error fetching feedback: {e}")
        return None


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
    
    feedback = {
        "id": str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "candidate_email": candidate_email,
        "candidate_name": candidate_name,
        "interview_date": datetime.now().isoformat() + "Z",
        "interviewer": interviewer,
        "role": role,
        "strengths": strengths,
        "concerns": concerns,
        "recommendation": recommendation,
        "score": score,
        "notes": notes,
    }
    
    client.upload_documents(documents=[feedback])
    
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
