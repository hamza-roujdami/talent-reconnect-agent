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
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
)

load_dotenv()

# Azure AI Search configuration
SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_KEY"]
INDEX_NAME = "feedback"


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
    
    # Create index
    index = SearchIndex(name=INDEX_NAME, fields=fields)
    
    # Delete if exists
    try:
        client.delete_index(INDEX_NAME)
        print(f"🗑️  Deleted existing '{INDEX_NAME}' index")
    except Exception:
        pass
    
    # Create new index
    client.create_index(index)
    print(f"✅ Created '{INDEX_NAME}' index")
    print(f"\nFields:")
    for field in fields:
        print(f"  - {field.name}: {field.type}")


if __name__ == "__main__":
    create_feedback_index()
