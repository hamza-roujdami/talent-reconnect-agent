#!/usr/bin/env python3
"""
01 - Create Azure AI Search Index

Creates the 'resumes' index schema with semantic search configuration.
Run this ONCE before uploading any documents.

Usage:
    python data/01-create-index.py
"""

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
KEY = os.environ.get("AZURE_SEARCH_API_KEY") or os.environ.get("AZURE_SEARCH_KEY")
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "resumes")

if not ENDPOINT or not KEY:
    print("❌ Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_API_KEY")
    exit(1)

# =============================================================================
# DEFINE INDEX SCHEMA
# =============================================================================

fields = [
    # Document key
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True),
    
    # Searchable text fields
    SearchableField(name="name", type=SearchFieldDataType.String),
    SearchableField(name="current_title", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SearchableField(name="current_company", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SearchableField(name="summary", type=SearchFieldDataType.String),
    SearchableField(name="location", type=SearchFieldDataType.String, filterable=True, facetable=True),
    
    # Skills collection
    SearchField(
        name="skills",
        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
        searchable=True,
        filterable=True,
        facetable=True,
    ),
    
    # Numeric/filterable fields
    SimpleField(name="experience_years", type=SearchFieldDataType.Int32, filterable=True, sortable=True, facetable=True),
    SimpleField(name="email", type=SearchFieldDataType.String),
    SimpleField(name="phone", type=SearchFieldDataType.String),
    
    # Education & certifications
    SearchableField(name="education", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SearchField(
        name="certifications",
        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
        searchable=True,
        filterable=True,
        facetable=True,
    ),
    
    # Boolean flag
    SimpleField(name="open_to_opportunities", type=SearchFieldDataType.Boolean, filterable=True, facetable=True),
    
    # Source URL for citations
    SimpleField(name="source_url", type=SearchFieldDataType.String),
]

# =============================================================================
# SEMANTIC CONFIGURATION
# =============================================================================

semantic_config = SemanticConfiguration(
    name="default",
    prioritized_fields=SemanticPrioritizedFields(
        title_field=SemanticField(field_name="current_title"),
        content_fields=[
            SemanticField(field_name="summary"),
            SemanticField(field_name="skills"),
        ],
        keywords_fields=[
            SemanticField(field_name="skills"),
            SemanticField(field_name="location"),
        ],
    ),
)

semantic_search = SemanticSearch(
    default_configuration_name="default",
    configurations=[semantic_config],
)

# =============================================================================
# CREATE INDEX
# =============================================================================

index = SearchIndex(
    name=INDEX_NAME,
    fields=fields,
    semantic_search=semantic_search,
)

client = SearchIndexClient(endpoint=ENDPOINT, credential=AzureKeyCredential(KEY))

try:
    # Delete if exists
    try:
        client.delete_index(INDEX_NAME)
        print(f"🗑️  Deleted existing index: {INDEX_NAME}")
    except Exception:
        pass
    
    # Create new index
    result = client.create_index(index)
    print(f"✅ Created index: {result.name}")
    print(f"   Fields: {len(result.fields)}")
    print(f"   Semantic config: {result.semantic_search.configurations[0].name}")

except Exception as e:
    print(f"❌ Failed to create index: {e}")
    exit(1)
finally:
    client.close()
