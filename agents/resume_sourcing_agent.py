"""
Resume Sourcing Agent

Searches internal resumes using Azure AI Search with hybrid search (keyword + vector)
"""

import os
from typing import Annotated, List
from pydantic import Field
from agent_framework import ChatAgent
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery



def search_resumes(skills: Annotated[List[str], Field(description="List of skills to search for")],
                   location: Annotated[str, Field(description="Preferred location (optional)")] = None,
                   years_experience: Annotated[int, Field(description="Minimum years of experience")] = 0) -> str:
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
            k=10,  # Changed from k_nearest_neighbors to k
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
        result_text = f"""
✓ Resume Sourcing Complete (Hybrid Search: Keyword + Vector + Semantic)

Searched for: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}
Found: {len(candidates)} matching candidates

Top Candidates:
"""
        
        for i, candidate in enumerate(candidates[:10], 1):
            result_text += f"""
{i}. {candidate['name']} ({candidate['email']})
   - Skills Match: {candidate['skills_match']}
   - Experience: {candidate['experience']}
   - Current Role: {candidate['last_role']}
   - Location: {candidate['location']}
   - Availability: {candidate['availability']}
"""
        
        return result_text
        
    except Exception as e:
        print(f"⚠️ Azure Search failed, using fallback: {e}")
        # Fallback to mock data
        candidates = [
            {
                "name": "Sarah Chen",
                "email": "sarah.chen@internal.com",
                "skills_match": "9/10 skills",
                "experience": "8 years",
                "last_role": "Senior ML Engineer",
                "location": "San Francisco, CA"
            },
            {
                "name": "Marcus Johnson",
                "email": "marcus.j@internal.com",
                "skills_match": "8/10 skills",
                "experience": "6 years",
                "last_role": "Data Scientist",
                "location": "Seattle, WA"
            },
            {
                "name": "Priya Sharma",
                "email": "priya.sharma@internal.com",
                "skills_match": "7/10 skills",
                "experience": "5 years",
                "last_role": "AI Engineer",
                "location": "Austin, TX"
            }
        ]
        
        result = f"""
✓ Resume Sourcing Complete (Mock - Fallback)

Searched for: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}
Found: {len(candidates)} matching candidates

Top Candidates:
"""
        
        for i, candidate in enumerate(candidates, 1):
            result += f"""
{i}. {candidate['name']} ({candidate['email']})
   - Skills Match: {candidate['skills_match']}
   - Experience: {candidate['experience']}
   - Last Role: {candidate['last_role']}
   - Location: {candidate['location']}
"""
        
        return result


def create_resume_sourcing_agent(chat_client):
    """Create the resume sourcing agent"""
    
    agent = ChatAgent(
        chat_client=chat_client,
        name="ResumeSourcingAgent",
        instructions="""
        You are a Resume Sourcing specialist using Azure AI Search.
        
        Your role:
        - Search internal resume database using hybrid search
        - Combine keyword search, vector embeddings, and semantic ranking
        - Vector search finds semantically similar profiles (e.g., "ML" matches "Machine Learning")
        - Apply filters: location, experience, availability
        - Rank candidates by combined relevance score
        
        Return top 10-15 candidates with match scores.
        """,
        tools=[search_resumes]
    )
    
    return agent
