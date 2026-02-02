"""Feedback lookup tool - connects to Azure AI Search feedback index."""

import os
import json
from typing import Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

load_dotenv()


def _get_feedback_client() -> SearchClient:
    """Create Azure AI Search client for feedback index."""
    endpoint = os.environ.get("SEARCH_SERVICE_ENDPOINT") or os.environ.get("AZURE_SEARCH_ENDPOINT")
    api_key = os.environ.get("SEARCH_SERVICE_API_KEY") or os.environ.get("AZURE_SEARCH_API_KEY")
    index_name = os.environ.get("SEARCH_FEEDBACK_INDEX", "feedback")
    
    if not endpoint or not api_key:
        raise RuntimeError("Missing SEARCH_SERVICE_ENDPOINT or SEARCH_SERVICE_API_KEY")
    
    return SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(api_key),
    )


def lookup_feedback(
    candidate_id: Optional[str] = None,
    candidate_name: Optional[str] = None,
    top: int = 5,
) -> str:
    """Get interview feedback for a candidate.
    
    Args:
        candidate_id: Candidate ID to look up
        candidate_name: Candidate name to search for
        top: Maximum number of feedback records
        
    Returns:
        JSON string with feedback records
    """
    client = _get_feedback_client()
    
    # Fields that exist in the feedback index
    select_fields = [
        "id", "candidate_id", "candidate_name", "candidate_email",
        "interviewer", "interview_date", "role", "score",
        "strengths", "concerns", "recommendation", "notes"
    ]
    
    try:
        if candidate_id:
            # Direct filter by candidate ID
            results = client.search(
                search_text="*",
                filter=f"candidate_id eq '{candidate_id}'",
                top=top,
                select=select_fields,
            )
        elif candidate_name:
            # Search by name
            results = client.search(
                search_text=candidate_name,
                top=top,
                select=select_fields,
            )
        else:
            return json.dumps({
                "error": "Must provide candidate_id or candidate_name",
                "feedback": []
            })
        
        feedback_records = []
        for result in results:
            feedback_records.append({
                "id": result.get("id"),
                "candidate_id": result.get("candidate_id"),
                "candidate_name": result.get("candidate_name"),
                "candidate_email": result.get("candidate_email"),
                "interviewer": result.get("interviewer"),
                "interview_date": result.get("interview_date"),
                "role": result.get("role"),
                "score": result.get("score"),
                "strengths": result.get("strengths", ""),
                "concerns": result.get("concerns", ""),
                "recommendation": result.get("recommendation"),
                "notes": (result.get("notes") or "")[:300],  # Truncate notes
            })
        
        if not feedback_records:
            return json.dumps({
                "count": 0,
                "feedback": [],
                "message": f"No feedback found for candidate"
            })
        
        return json.dumps({
            "count": len(feedback_records),
            "feedback": feedback_records,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to lookup feedback"
        })


# Async version for V2 agents
async def lookup_feedback_async(
    candidate_id: Optional[str] = None,
    candidate_name: Optional[str] = None,
    top: int = 5,
) -> str:
    """Async wrapper for lookup_feedback."""
    import asyncio
    return await asyncio.to_thread(lookup_feedback, candidate_id, candidate_name, top)
