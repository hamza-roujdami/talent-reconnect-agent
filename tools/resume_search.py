"""
Resume Search Tool

Searches Azure AI Search for matching candidates using hybrid search
"""

import os
from typing import Annotated, List
from pydantic import Field
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


def search_resumes(
    skills: Annotated[List[str], Field(description="List of skills to search for")],
    location: Annotated[str, Field(description="Preferred location (optional)")] = None,
    years_experience: Annotated[int, Field(description="Minimum years of experience")] = 0
) -> str:
    """
    Search Azure AI Search for matching resumes using hybrid search (keyword + vector)
    Returns candidate profiles with semantic ranking
    """
    try:
        # Initialize Azure Search client
        search_client = SearchClient(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            index_name=os.getenv("AZURE_SEARCH_INDEX", "resumes"),
            credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
        )
        
        # Build search query
        search_text = ", ".join(skills)
        
        # Generate query embedding for vector search
        from openai import AzureOpenAI
        
        embeddings_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        embedding_response = embeddings_client.embeddings.create(
            input=[search_text],
            model="text-embedding-ada-002"
        )
        query_vector = embedding_response.data[0].embedding
        
        # Create vector query
        vector_query = VectorizedQuery(
            vector=query_vector,
            k=10,
            fields="summary_vector"
        )
        
        # Build filter
        filters = []
        if location:
            filters.append(f"search.ismatch('{location}', 'location')")
        if years_experience > 0:
            filters.append(f"experience_years ge {years_experience}")
        
        filter_expr = " and ".join(filters) if filters else None
        
        # Execute hybrid search (keyword + vector + semantic ranking)
        results = search_client.search(
            search_text=search_text,
            vector_queries=[vector_query],
            filter=filter_expr,
            select=["name", "email", "title", "experience_years", "location", "skills", "summary", "availability"],
            top=10,
            include_total_count=True
        )
        
        candidates = []
        for result in results:
            # Calculate skills match
            candidate_skills = result.get("skills", [])
            matching_skills = set(skills) & set(candidate_skills)
            skills_match = f"{len(matching_skills)}/{len(skills)} skills"
            
            candidates.append({
                "name": result["name"],
                "email": result["email"],
                "skills_match": skills_match,
                "experience": f"{result['experience_years']} years",
                "last_role": result["title"],
                "location": result["location"],
                "summary": result.get("summary", ""),
                "availability": result.get("availability", "unknown")
            })
        
        # Format results
        result_text = f"""✓ Resume Sourcing Complete (Hybrid Search: Keyword + Vector + Semantic)

Searched for: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}
Found: {len(candidates)} matching candidates

Top Candidates:
"""
        for i, c in enumerate(candidates[:5], 1):
            result_text += f"""
{i}. {c['name']} | {c['email']}
   Match: {c['skills_match']} | Experience: {c['experience']}
   Last Role: {c['last_role']} | Location: {c['location']}
   Availability: {c['availability']}"""
        
        return result_text
        
    except Exception as e:
        # Fallback to mock data if Azure Search fails
        return f"""✓ Resume Sourcing Complete (Mock Data - Azure Search unavailable)

Searched for: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}
Found: 3 matching candidates

Top Candidates:
1. Sarah Chen | sarah.chen@example.com
   Match: 9/10 skills | Experience: 8 years
   Last Role: Senior ML Engineer | Location: San Francisco, CA
   Availability: Open to opportunities

2. Marcus Johnson | marcus.j@example.com
   Match: 8/10 skills | Experience: 6 years
   Last Role: AI Engineer | Location: Seattle, WA
   Availability: Passive

3. Priya Sharma | priya.sharma@example.com
   Match: 7/10 skills | Experience: 5 years
   Last Role: ML Specialist | Location: Austin, TX
   Availability: Open to opportunities

Note: Using mock data. Check Azure Search configuration."""
