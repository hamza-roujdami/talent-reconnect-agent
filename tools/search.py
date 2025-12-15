"""
Search Tool - Resume Search using Azure AI Search

Searches 100k+ resumes with Lucene full-text search.
"""

import os
import httpx
from typing import Annotated, List
from pydantic import Field


def search_resumes(
    skills: Annotated[List[str], Field(description="Required skills to search for (e.g., ['Python', 'FastAPI', 'Azure'])")],
    job_title: Annotated[str, Field(description="Target job title (e.g., 'Senior Python Developer')")] = "",
    min_experience: Annotated[int, Field(description="Minimum years of experience required")] = 0,
    location: Annotated[str, Field(description="Preferred location (e.g., 'UAE', 'Remote')")] = "",
    top_k: Annotated[int, Field(description="Number of candidates to return")] = 5,
) -> str:
    """
    Search resumes in Azure AI Search.
    Returns top matching candidates with their profiles.
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
    filter_expr = ""
    if min_experience > 0:
        filter_expr = f"experience_years ge {min_experience}"
    
    # Search request
    url = f"{endpoint}/indexes/{index}/docs/search?api-version=2023-11-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": key,
    }
    body = {
        "search": query,
        "top": top_k,
        "select": "name,current_title,skills,experience_years,location,email,summary,current_company",
        "queryType": "simple",
    }
    if filter_expr:
        body["filter"] = filter_expr
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        return f"❌ Search failed: {str(e)}"
    
    results = data.get("value", [])
    
    if not results:
        return f"No candidates found matching: {query}. Try broadening your search criteria."
    
    # Format results
    output = f"""## 🔍 Found {len(results)} Matching Candidates

**Search:** {query}
**Experience:** {min_experience}+ years

---
"""
    
    for i, r in enumerate(results, 1):
        name = r.get("name", "Unknown")
        title = r.get("current_title", "N/A")
        company = r.get("current_company", "N/A")
        skills_list = r.get("skills", [])
        exp = r.get("experience_years", "N/A")
        loc = r.get("location", "N/A")
        email = r.get("email", "N/A")
        summary = r.get("summary", "")[:200]
        
        # Handle skills as list or string
        if isinstance(skills_list, list):
            skills_str = ", ".join(skills_list[:6])
        else:
            skills_str = str(skills_list)
        
        output += f"""
### {i}. {name}
- **Title:** {title} at {company}
- **Experience:** {exp} years
- **Location:** {loc}
- **Skills:** {skills_str}
- **Email:** {email}
- **Summary:** {summary}...

"""
    
    output += "\n---\n**Which candidates would you like to reach out to?**"
    
    return output
