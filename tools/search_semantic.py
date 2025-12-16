"""
Search Tool - Semantic Search (Neural Reranking)

Uses Azure SDK (same as MAF's AzureAISearchContextProvider).
Hybrid search with semantic understanding (+15-25% relevance).

Best for: Natural language queries, finding conceptually similar candidates.

How it works:
1. BM25 keyword search (baseline)
2. Neural reranker scores results by MEANING
3. Understands: "ML" = "Machine Learning", "UAE" ≈ "Dubai"
"""

import os
from typing import Annotated, List
from pydantic import Field
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType


def search_resumes_semantic(
    skills: Annotated[List[str], Field(description="Required skills to search for (e.g., ['Python', 'FastAPI', 'Azure'])")],
    job_title: Annotated[str, Field(description="Target job title (e.g., 'Senior Python Developer')")] = "",
    min_experience: Annotated[int, Field(description="Minimum years of experience required")] = 0,
    location: Annotated[str, Field(description="Preferred location (e.g., 'UAE', 'Remote')")] = "",
    top_k: Annotated[int, Field(description="Number of candidates to return")] = 5,
) -> str:
    """
    Search resumes using semantic ranking.
    Uses Azure SDK - same as MAF's AzureAISearchContextProvider.
    Understands meaning and context - finds candidates even without exact keyword matches.
    """
    
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    key = os.environ.get("AZURE_SEARCH_KEY")
    index = os.environ.get("AZURE_SEARCH_INDEX", "resumes")
    
    if not endpoint or not key:
        return "❌ Azure AI Search not configured. Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY."
    
    # Build search query
    search_terms = []
    if job_title:
        search_terms.append(job_title)
    search_terms.extend(skills)
    if location:
        search_terms.append(location)
    
    query = " ".join(search_terms)
    
    # Build filter for experience
    filter_expr = None
    if min_experience > 0:
        filter_expr = f"experience_years ge {min_experience}"
    
    # Create Azure SDK client (same as MAF uses)
    client = SearchClient(
        endpoint=endpoint,
        index_name=index,
        credential=AzureKeyCredential(key),
    )
    
    try:
        # Semantic search - with semantic configuration (same as MAF)
        results = client.search(
            search_text=query,
            top=top_k,
            select=["name", "current_title", "skills", "experience_years", "location", "email", "summary", "current_company"],
            filter=filter_expr,
            query_type=QueryType.SEMANTIC,  # Enable semantic ranking
            semantic_configuration_name="default",  # Must match index config
        )
        
        results_list = list(results)
    except Exception as e:
        return f"❌ Search failed: {str(e)}"
    finally:
        client.close()
    
    if not results_list:
        return f"No candidates found matching: {query}. Try broadening your search criteria."
    
    # Format results
    output = f"""## 🔍 Found {len(results_list)} Candidates (Semantic Search)

**Search:** {query}
**Method:** Neural reranking (+15-25% relevance) via Azure SDK
**Experience:** {min_experience}+ years

---
"""
    
    for i, r in enumerate(results_list, 1):
        # Get semantic reranker score
        score = getattr(r, '@search.reranker_score', None) or r.get('@search.reranker_score')
        output += _format_candidate(i, dict(r), score)
    
    output += "\n---\n**Which candidates would you like to reach out to?**"
    return output


def _format_candidate(i: int, r: dict, score=None) -> str:
    """Format a single candidate result."""
    name = r.get("name", "Unknown")
    title = r.get("current_title", "N/A")
    company = r.get("current_company", "N/A")
    skills_list = r.get("skills", [])
    exp = r.get("experience_years", "N/A")
    loc = r.get("location", "N/A")
    email = r.get("email", "N/A")
    summary = r.get("summary", "")[:200]
    
    if isinstance(skills_list, list):
        skills_str = ", ".join(skills_list[:6])
    else:
        skills_str = str(skills_list)
    
    score_str = f" (relevance: {score:.2f})" if isinstance(score, (int, float)) else ""
    
    return f"""
### {i}. {name}{score_str}
- **Title:** {title} at {company}
- **Experience:** {exp} years
- **Location:** {loc}
- **Skills:** {skills_str}
- **Email:** {email}
- **Summary:** {summary}...

"""
