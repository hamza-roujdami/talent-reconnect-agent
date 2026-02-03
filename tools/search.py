"""Candidate search tool - connects to Azure AI Search resumes index."""

import os
import json
from typing import Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

load_dotenv()


def _get_search_client() -> SearchClient:
    """Create Azure AI Search client for resumes index."""
    endpoint = os.environ.get("SEARCH_SERVICE_ENDPOINT") or os.environ.get("AZURE_SEARCH_ENDPOINT")
    api_key = os.environ.get("SEARCH_SERVICE_API_KEY") or os.environ.get("AZURE_SEARCH_API_KEY")
    index_name = os.environ.get("SEARCH_RESUME_INDEX", "resumes")
    
    if not endpoint or not api_key:
        raise RuntimeError("Missing SEARCH_SERVICE_ENDPOINT or SEARCH_SERVICE_API_KEY")
    
    return SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(api_key),
    )


def search_candidates(
    query: str,
    location: Optional[str] = None,
    skills: Optional[list[str]] = None,
    top: int = 10,
) -> str:
    """Search for candidates matching criteria.
    
    Args:
        query: Search query (job title, skills, keywords)
        location: Optional location filter
        skills: Optional list of required skills
        top: Number of results to return
        
    Returns:
        JSON string with matching candidates
    """
    client = _get_search_client()
    
    # Build filter expression
    filters = []
    if location:
        # Use search.ismatch for location matching
        filters.append(f"search.ismatch('{location}', 'location')")
    
    filter_expr = " and ".join(filters) if filters else None
    
    # Build search text
    search_text = query
    if skills:
        search_text += " " + " ".join(skills)
    
    try:
        # Use semantic search (requires Standard tier + semantic enabled)
        results = client.search(
            search_text=search_text,
            query_type="semantic",
            semantic_configuration_name="default",
            filter=filter_expr,
            top=top,
            select=["id", "name", "current_title", "current_company", "location", "skills", "experience_years", "summary"],
        )
        
        candidates = []
        for result in results:
            candidates.append({
                "id": result.get("id"),
                "name": result.get("name"),
                "title": result.get("current_title"),
                "company": result.get("current_company"),
                "location": result.get("location"),
                "skills": result.get("skills", [])[:10],
                "experience_years": result.get("experience_years"),
                "summary": result.get("summary", "")[:200],
            })
        
        if not candidates:
            return json.dumps({
                "count": 0,
                "candidates": [],
                "message": f"No candidates found for: {query}"
            })
        
        return json.dumps({
            "count": len(candidates),
            "candidates": candidates,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to search candidates"
        })


# Async version for V2 agents
async def search_candidates_async(
    query: str,
    location: Optional[str] = None,
    skills: Optional[list[str]] = None,
    top: int = 10,
) -> str:
    """Async wrapper for search_candidates."""
    # Azure Search SDK is sync, so we just call the sync version
    # In production, you'd use asyncio.to_thread or an async client
    import asyncio
    return await asyncio.to_thread(search_candidates, query, location, skills, top)
