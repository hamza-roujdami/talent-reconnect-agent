"""Tool for TalentScout to retrieve and display candidates from Azure AI Search."""

from __future__ import annotations

import os
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from dotenv import load_dotenv

load_dotenv()


def _get_env(*names: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    if required:
        raise RuntimeError(f"Missing env var: {names}")
    return default


# Shared search client
_search_client: Optional[SearchClient] = None


def _get_search_client() -> SearchClient:
    """Get or create Azure AI Search client."""
    global _search_client
    
    if _search_client is None:
        endpoint = _get_env("SEARCH_SERVICE_ENDPOINT", "AZURE_SEARCH_ENDPOINT", required=True)
        api_key = _get_env("SEARCH_SERVICE_API_KEY", "AZURE_SEARCH_API_KEY", "AZURE_SEARCH_KEY")
        index_name = _get_env("SEARCH_RESUME_INDEX", "AZURE_SEARCH_INDEX_NAME", default="resumes")
        
        cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
        _search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=cred,
        )
    
    return _search_client


def search_candidates(query: str, top_k: int = 10) -> str:
    """
    Search for candidates matching the given criteria.
    
    Args:
        query: Search query describing the ideal candidate (e.g., "Python developer with Azure experience in Dubai")
        top_k: Maximum number of candidates to return (default 10)
        
    Returns:
        Markdown table of matching candidates with their details.
        
    IMPORTANT: You MUST call this tool to get candidates. Do not make up candidate data.
    """
    client = _get_search_client()
    semantic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG", "default")
    
    try:
        results = client.search(
            search_text=query,
            top=top_k,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name=semantic_config,
        )
        
        candidates = []
        for doc in results:
            candidates.append({
                "id": doc.get("id", ""),
                "email": doc.get("email", ""),
                "name": doc.get("name", ""),
                "title": doc.get("current_title", ""),
                "company": doc.get("current_company", ""),
                "location": doc.get("location", ""),
                "experience": doc.get("experience_years", ""),
                "skills": ", ".join(doc.get("skills", [])[:6]),
            })
        
        if not candidates:
            return "No matching candidates found. Try broadening your search criteria."
        
        # Build markdown table
        lines = [
            "**📊 Top Matching Candidates:**\n",
            "| # | Name | Email | Title | Company | Location | Exp | Key Skills |",
            "|---|------|-------|-------|---------|----------|-----|------------|",
        ]
        
        for i, c in enumerate(candidates, 1):
            lines.append(
                f"| {i} | {c['name']} | {c['email']} | {c['title']} | "
                f"{c['company']} | {c['location']} | {c['experience']} yrs | {c['skills']} |"
            )
        
        lines.append("\n**Next steps:** Say 'details for candidate 1' or 'check feedback for candidate 2'")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"Search error: {str(e)}"
