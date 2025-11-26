"""
Setup Azure AI Search for Resume Sourcing

Creates search index and uploads sample resume data
"""

import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearchAlgorithmKind
)


# Azure Search configuration
SEARCH_SERVICE_NAME = "talent-search-44665"
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE_NAME}.search.windows.net"
SEARCH_ADMIN_KEY = "vod2KJA2xKMO0uLjtHC8WNlYJQJVHnJJkl0orBhO7sAzSeCC4R3K"
INDEX_NAME = "resumes"

# Azure OpenAI configuration for embeddings
AZURE_OPENAI_ENDPOINT = "https://uaenorth.api.cognitive.microsoft.com/"
AZURE_OPENAI_KEY = "d97f2e6f37244b87975682a45ba30798"
EMBEDDING_MODEL = "text-embedding-ada-002"


def generate_embeddings(texts):
    """Generate embeddings for text using Azure OpenAI"""
    from openai import AzureOpenAI
    
    # Create Azure OpenAI client
    client = AzureOpenAI(
        api_key=AZURE_OPENAI_KEY,
        api_version="2024-02-01",
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    )
    
    # Generate embeddings
    response = client.embeddings.create(
        input=texts,
        model=EMBEDDING_MODEL
    )
    
    return [item.embedding for item in response.data]


def create_search_index():
    """Create the search index with fields for resume data"""
    
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_ADMIN_KEY)
    )
    
    # Delete existing index if it exists
    try:
        index_client.delete_index(INDEX_NAME)
        print(f"Deleted existing index '{INDEX_NAME}'")
    except:
        pass
    
    # Define index schema
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="name", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchableField(name="email", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="experience_years", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchableField(name="location", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="skills",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
            facetable=True
        ),
        SearchableField(name="summary", type=SearchFieldDataType.String),
        SearchableField(name="current_company", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="availability", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="summary_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="resume-vector-profile"
        )
    ]
    
    # Configure vector search with HNSW algorithm
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="resume-hnsw",
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="resume-vector-profile",
                algorithm_configuration_name="resume-hnsw"
            )
        ]
    )
    
    # Create semantic configuration for better relevance
    semantic_config = SemanticConfiguration(
        name="resume-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[
                SemanticField(field_name="summary"),
                SemanticField(field_name="skills")
            ]
        )
    )
    
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    # Create the index
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        semantic_search=semantic_search,
        vector_search=vector_search
    )
    
    print(f"Creating index '{INDEX_NAME}'...")
    result = index_client.create_or_update_index(index)
    print(f"✓ Index '{result.name}' created successfully")


def upload_resume_data():
    """Upload sample resume data to the search index"""
    
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_ADMIN_KEY)
    )
    
    # Load sample data
    data_file = os.path.join(os.path.dirname(__file__), "sample_resumes.json")
    with open(data_file, "r") as f:
        documents = json.load(f)
    
    # Generate embeddings for summaries
    print(f"\nGenerating embeddings for {len(documents)} resumes...")
    summaries = [doc["summary"] for doc in documents]
    embeddings = generate_embeddings(summaries)
    
    # Add embeddings to documents
    for doc, embedding in zip(documents, embeddings):
        doc["summary_vector"] = embedding
    
    print(f"Uploading {len(documents)} resume documents with embeddings...")
    result = search_client.upload_documents(documents=documents)
    
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"✓ Successfully uploaded {succeeded}/{len(documents)} documents")
    
    # Verify the upload
    print(f"\n✓ Search service ready at: {SEARCH_ENDPOINT}")
    print(f"✓ Index name: {INDEX_NAME}")
    print(f"✓ Total documents: {succeeded}")


if __name__ == "__main__":
    print("="*60)
    print("Azure AI Search Setup for Resume Sourcing")
    print("="*60)
    
    try:
        create_search_index()
        upload_resume_data()
        
        print("\n" + "="*60)
        print("✓ Setup Complete!")
        print("="*60)
        print("\nAdd these to your .env file:")
        print(f"AZURE_SEARCH_ENDPOINT={SEARCH_ENDPOINT}")
        print(f"AZURE_SEARCH_KEY={SEARCH_ADMIN_KEY}")
        print(f"AZURE_SEARCH_INDEX={INDEX_NAME}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
