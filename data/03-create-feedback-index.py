"""
Create Azure AI Search index for interview feedback.

This creates a 'feedback' index that links to the 'resumes' index via candidate_id.

Index Schema:
- id: Unique feedback record ID
- candidate_id: Links to resume (foreign key)
- candidate_email: For easy lookup
- candidate_name: Denormalized for display
- interview_date: When the interview happened
- interviewer: Who conducted the interview
- role: Role being interviewed for
- strengths: Observed strengths
- concerns: Any concerns or red flags
- recommendation: strong_hire | hire | maybe | no_hire
- score: Interview score (0-100)
- notes: Additional notes

Usage:
    python 04-create-feedback-index.py
"""
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
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

# Azure AI Search configuration
SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ.get("AZURE_SEARCH_API_KEY") or os.environ.get("AZURE_SEARCH_KEY")
if not SEARCH_KEY:
    raise RuntimeError("Set AZURE_SEARCH_API_KEY (or legacy AZURE_SEARCH_KEY) before running this script.")
INDEX_NAME = os.environ.get("AZURE_FEEDBACK_INDEX_NAME", "feedback")
SEMANTIC_CONFIG_NAME = os.environ.get("AZURE_FEEDBACK_SEMANTIC_CONFIG", "feedback-semantic")


def create_feedback_index():
    """Create the feedback index schema."""
    
    # Create index client
    client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_KEY),
    )
    
    # Define fields
    fields = [
        # Primary key
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
        ),
        # Link to resume
        SimpleField(
            name="candidate_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="candidate_email",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="candidate_name",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        # Interview metadata
        SimpleField(
            name="interview_date",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SearchableField(
            name="interviewer",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="role",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        # Feedback content
        SearchableField(
            name="strengths",
            type=SearchFieldDataType.String,
        ),
        SearchableField(
            name="concerns",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="recommendation",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,  # strong_hire, hire, maybe, no_hire
        ),
        SimpleField(
            name="score",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SearchableField(
            name="notes",
            type=SearchFieldDataType.String,
        ),
    ]
    
    semantic_settings = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG_NAME,
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[
                        SemanticField(field_name="notes"),
                        SemanticField(field_name="strengths"),
                        SemanticField(field_name="concerns"),
                    ],
                    keywords_fields=[
                        SemanticField(field_name="candidate_name"),
                        SemanticField(field_name="role"),
                    ],
                ),
            )
        ]
    )

    index = SearchIndex(name=INDEX_NAME, fields=fields, semantic_search=semantic_settings)

    try:
        client.get_index(INDEX_NAME)
        exists = True
    except ResourceNotFoundError:
        exists = False

    if exists:
        client.create_or_update_index(index)
        action = "♻️  Updated"
    else:
        client.create_index(index)
        action = "✅ Created"

    print(f"{action} '{INDEX_NAME}' index with semantic config '{SEMANTIC_CONFIG_NAME}'")
    print("\nFields:")
    for field in fields:
        print(f"  - {field.name}: {field.type}")


if __name__ == "__main__":
    create_feedback_index()
