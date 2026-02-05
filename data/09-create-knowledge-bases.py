#!/usr/bin/env python
"""Create Foundry IQ Knowledge Sources and Knowledge Bases.

Flow:
1. Create Knowledge Sources (wrap existing search indexes)
2. Create Knowledge Bases (reference the sources with LLM for query planning)

Usage:
    python data/09-create-knowledge-bases.py
    
Requirements:
    pip install azure-search-documents==11.7.0b2
"""

import asyncio
import os
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
    SearchIndexFieldReference,
    KnowledgeBase,
    KnowledgeSourceReference,
    KnowledgeBaseAzureOpenAIModel,
    AzureOpenAIVectorizerParameters,
    KnowledgeRetrievalOutputMode,
    KnowledgeRetrievalMinimalReasoningEffort,
)
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "https://nkg3search.search.windows.net")
SEARCH_API_KEY = os.environ.get("AZURE_SEARCH_API_KEY")

# Azure OpenAI for query planning (from Foundry)
AOAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AOAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AOAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


def get_client():
    """Get SearchIndexClient with auth."""
    if SEARCH_API_KEY:
        return SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_API_KEY))
    else:
        return SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=DefaultAzureCredential())


def create_knowledge_source(
    client: SearchIndexClient,
    name: str,
    description: str,
    index_name: str,
    semantic_config: str = "default",
    source_fields: list[str] = None,
):
    """Create a search index knowledge source.
    
    Args:
        client: SearchIndexClient instance
        name: Knowledge source name (e.g., "resumes-ks")
        description: Human-readable description
        index_name: Target search index name
        semantic_config: Semantic configuration name on the index
        source_fields: Fields to include in citations
    """
    source_data_fields = []
    if source_fields:
        source_data_fields = [SearchIndexFieldReference(name=f) for f in source_fields]
    
    knowledge_source = SearchIndexKnowledgeSource(
        name=name,
        description=description,
        search_index_parameters=SearchIndexKnowledgeSourceParameters(
            search_index_name=index_name,
            semantic_configuration_name=semantic_config,
            source_data_fields=source_data_fields,
        )
    )
    
    try:
        client.create_or_update_knowledge_source(knowledge_source)
        print(f"✓ Created knowledge source: {name} -> {index_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to create knowledge source {name}: {e}")
        return False


def create_knowledge_base(
    client: SearchIndexClient,
    name: str,
    description: str,
    source_names: list[str],
    retrieval_instructions: str = None,
    answer_instructions: str = None,
    use_llm: bool = False,
):
    """Create a knowledge base referencing knowledge sources.
    
    Args:
        client: SearchIndexClient instance
        name: Knowledge base name (e.g., "resumes-kb")
        description: Human-readable description
        source_names: List of knowledge source names to include
        retrieval_instructions: Prompt for LLM query planning
        answer_instructions: Prompt for answer synthesis
        use_llm: Whether to enable LLM for query planning
    """
    # Build knowledge source references
    knowledge_sources = [KnowledgeSourceReference(name=s) for s in source_names]
    
    # LLM configuration (optional - for query planning)
    models = []
    if use_llm and AOAI_ENDPOINT and AOAI_API_KEY:
        aoai_params = AzureOpenAIVectorizerParameters(
            resource_url=AOAI_ENDPOINT,
            api_key=AOAI_API_KEY,
            deployment_name=AOAI_DEPLOYMENT,
            model_name=AOAI_DEPLOYMENT,
        )
        models = [KnowledgeBaseAzureOpenAIModel(azure_open_ai_parameters=aoai_params)]
    
    # Use minimal reasoning (no LLM needed) - agent handles query planning
    knowledge_base = KnowledgeBase(
        name=name,
        description=description,
        retrieval_instructions=retrieval_instructions,
        answer_instructions=answer_instructions,
        output_mode=KnowledgeRetrievalOutputMode.EXTRACTIVE_DATA,  # Return raw results for agent processing
        knowledge_sources=knowledge_sources,
        models=models,
        retrieval_reasoning_effort=KnowledgeRetrievalMinimalReasoningEffort(),  # Instantiate the class
    )
    
    try:
        client.create_or_update_knowledge_base(knowledge_base)
        print(f"✓ Created knowledge base: {name} (sources: {source_names})")
        return True
    except Exception as e:
        print(f"✗ Failed to create knowledge base {name}: {e}")
        return False


def list_existing(client: SearchIndexClient):
    """List existing knowledge sources and bases."""
    print("Existing knowledge sources:")
    try:
        sources = list(client.list_knowledge_sources())
        for s in sources:
            print(f"  - {s.name}")
        if not sources:
            print("  (none)")
    except Exception as e:
        print(f"  Error listing: {e}")
    
    print("Existing knowledge bases:")
    try:
        bases = list(client.list_knowledge_bases())
        for b in bases:
            print(f"  - {b.name}")
        if not bases:
            print("  (none)")
    except Exception as e:
        print(f"  Error listing: {e}")


def main():
    print(f"Search endpoint: {SEARCH_ENDPOINT}")
    print()
    
    client = get_client()
    list_existing(client)
    print()
    
    # === Step 1: Create Knowledge Sources ===
    print("=== Creating Knowledge Sources ===")
    
    # Resumes knowledge source
    create_knowledge_source(
        client,
        name="resumes-ks",
        description="Candidate resumes with skills, experience, location, and job history. Use for talent search queries.",
        index_name="resumes",
        semantic_config="default",
        source_fields=["name", "current_title", "location", "experience_years", "email"],
    )
    
    # Feedback knowledge source
    create_knowledge_source(
        client,
        name="feedback-ks", 
        description="Interview feedback and candidate history. Use for checking past interview performance.",
        index_name="feedback",
        semantic_config="default",
        source_fields=["candidate_name", "interviewer", "score", "interview_date"],
    )
    
    print()
    
    # === Step 2: Create Knowledge Bases ===
    print("=== Creating Knowledge Bases ===")
    
    # Resumes KB (no LLM - agent handles reasoning)
    create_knowledge_base(
        client,
        name="resumes-kb",
        description="Talent search knowledge base for finding candidates by skills, experience, and location.",
        source_names=["resumes-ks"],
        retrieval_instructions=None,  # No LLM, so no instructions
        answer_instructions=None,
        use_llm=False,  # Agent handles LLM, keep KB simple
    )
    
    # Feedback KB (no LLM - agent handles reasoning)
    create_knowledge_base(
        client,
        name="feedback-kb",
        description="Interview feedback knowledge base for checking candidate history.",
        source_names=["feedback-ks"],
        retrieval_instructions=None,  # No LLM, so no instructions
        answer_instructions=None,
        use_llm=False,
    )
    
    print()
    print("Done! Knowledge sources and bases created.")
    print()
    print("Next step: Run data/10-create-mcp-connections.py to create project connections")


if __name__ == "__main__":
    main()
