#!/usr/bin/env python3
"""
Setup Azure AI Search Index for Talent Reconnect Agent

This script:
1. Creates the 'resumes' index with the required schema
2. Optionally uploads sample data for testing
3. Can bulk upload resumes from JSON/CSV files

Usage:
    python scripts/setup_search.py                    # Create index only
    python scripts/setup_search.py --sample           # Create index + sample data
    python scripts/setup_search.py --file data.json   # Upload from JSON file
    python scripts/setup_search.py --file data.csv    # Upload from CSV file

Prerequisites:
    pip install azure-search-documents python-dotenv pandas
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Check dependencies
try:
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SearchField,
        SearchFieldDataType,
        SimpleField,
        SearchableField,
    )
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
except ImportError:
    print("❌ Missing dependency: azure-search-documents")
    print("   Run: pip install azure-search-documents")
    sys.exit(1)


def get_credentials():
    """Get Azure AI Search credentials from environment."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX", "resumes")
    
    if not endpoint or not key:
        print("❌ Missing environment variables. Set in .env:")
        print("   AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net")
        print("   AZURE_SEARCH_KEY=your-admin-key")
        sys.exit(1)
    
    return endpoint, key, index_name


def create_index(endpoint: str, key: str, index_name: str) -> bool:
    """Create the resumes index with required schema."""
    credential = AzureKeyCredential(key)
    client = SearchIndexClient(endpoint=endpoint, credential=credential)
    
    # Define index schema matching our search tool
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="name", type=SearchFieldDataType.String),
        SimpleField(name="email", type=SearchFieldDataType.String),
        SearchableField(name="job_title", type=SearchFieldDataType.String),
        SimpleField(name="experience_years", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="location", type=SearchFieldDataType.String, filterable=True),
        SearchableField(
            name="skills",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),
    ]
    
    index = SearchIndex(name=index_name, fields=fields)
    
    try:
        result = client.create_or_update_index(index)
        print(f"✅ Index '{result.name}' created/updated")
        print(f"   Endpoint: {endpoint}")
        print(f"   Fields: id, name, email, job_title, experience_years, location, skills")
        return True
    except Exception as e:
        print(f"❌ Failed to create index: {e}")
        return False


def upload_documents(endpoint: str, key: str, index_name: str, documents: list) -> int:
    """Upload documents to the index in batches."""
    credential = AzureKeyCredential(key)
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    
    batch_size = 1000
    total_uploaded = 0
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        try:
            result = client.upload_documents(documents=batch)
            succeeded = sum(1 for r in result if r.succeeded)
            total_uploaded += succeeded
            print(f"   Uploaded batch {i//batch_size + 1}: {succeeded}/{len(batch)} documents")
        except Exception as e:
            print(f"   ❌ Batch {i//batch_size + 1} failed: {e}")
    
    return total_uploaded


def upload_sample_data(endpoint: str, key: str, index_name: str) -> bool:
    """Upload sample resume data for testing."""
    sample_resumes = [
        {
            "id": "sample-001",
            "name": "Ahmed Hassan",
            "email": "ahmed.hassan@example.com",
            "job_title": "Senior ML Engineer",
            "experience_years": 6,
            "location": "Dubai, UAE",
            "skills": ["Python", "TensorFlow", "PyTorch", "Azure ML", "Kubernetes"],
        },
        {
            "id": "sample-002",
            "name": "Sara Al-Maktoum",
            "email": "sara.almaktoum@example.com",
            "job_title": "AI Research Scientist",
            "experience_years": 4,
            "location": "Abu Dhabi, UAE",
            "skills": ["Python", "NLP", "Transformers", "LangChain", "OpenAI"],
        },
        {
            "id": "sample-003",
            "name": "Michael Chen",
            "email": "michael.chen@example.com",
            "job_title": "Data Engineer",
            "experience_years": 5,
            "location": "Remote (Singapore)",
            "skills": ["Python", "Spark", "Databricks", "Azure Data Factory", "SQL"],
        },
        {
            "id": "sample-004",
            "name": "Fatima Al-Zahra",
            "email": "fatima.alzahra@example.com",
            "job_title": "Full Stack Developer",
            "experience_years": 3,
            "location": "Sharjah, UAE",
            "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
        },
        {
            "id": "sample-005",
            "name": "James Wilson",
            "email": "james.wilson@example.com",
            "job_title": "DevOps Engineer",
            "experience_years": 7,
            "location": "Dubai, UAE",
            "skills": ["Azure", "Terraform", "Kubernetes", "GitHub Actions", "Python"],
        },
        {
            "id": "sample-006",
            "name": "Layla Ibrahim",
            "email": "layla.ibrahim@example.com",
            "job_title": "Senior AI Engineer",
            "experience_years": 8,
            "location": "Abu Dhabi, UAE",
            "skills": ["Python", "TensorFlow", "Computer Vision", "MLOps", "Azure"],
        },
        {
            "id": "sample-007",
            "name": "Omar Khan",
            "email": "omar.khan@example.com",
            "job_title": "Backend Developer",
            "experience_years": 4,
            "location": "Dubai, UAE",
            "skills": ["Python", "Django", "PostgreSQL", "Redis", "Docker"],
        },
        {
            "id": "sample-008",
            "name": "Nina Patel",
            "email": "nina.patel@example.com",
            "job_title": "Machine Learning Engineer",
            "experience_years": 5,
            "location": "Remote (India)",
            "skills": ["Python", "scikit-learn", "XGBoost", "Feature Engineering", "SQL"],
        },
        {
            "id": "sample-009",
            "name": "Khalid Al-Rashid",
            "email": "khalid.alrashid@example.com",
            "job_title": "Cloud Architect",
            "experience_years": 10,
            "location": "Abu Dhabi, UAE",
            "skills": ["Azure", "AWS", "Terraform", "Kubernetes", "Security"],
        },
        {
            "id": "sample-010",
            "name": "Emily Zhang",
            "email": "emily.zhang@example.com",
            "job_title": "NLP Engineer",
            "experience_years": 3,
            "location": "Dubai, UAE",
            "skills": ["Python", "Transformers", "spaCy", "BERT", "GPT"],
        },
    ]
    
    print(f"\n📄 Uploading {len(sample_resumes)} sample resumes...")
    uploaded = upload_documents(endpoint, key, index_name, sample_resumes)
    print(f"✅ Uploaded {uploaded}/{len(sample_resumes)} sample resumes")
    return uploaded > 0


def load_json_file(file_path: str) -> list:
    """Load resumes from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Handle both array and object with 'value' key
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'value' in data:
        return data['value']
    else:
        raise ValueError("JSON must be an array or object with 'value' key")


def load_csv_file(file_path: str) -> list:
    """Load resumes from CSV file."""
    try:
        import pandas as pd
    except ImportError:
        print("❌ CSV support requires pandas: pip install pandas")
        sys.exit(1)
    
    df = pd.read_csv(file_path)
    
    # Convert skills column from string to list if needed
    if 'skills' in df.columns and df['skills'].dtype == 'object':
        df['skills'] = df['skills'].apply(lambda x: x.split(',') if isinstance(x, str) else [])
    
    return df.to_dict('records')


def upload_from_file(endpoint: str, key: str, index_name: str, file_path: str) -> bool:
    """Upload resumes from a JSON or CSV file."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"\n📄 Loading resumes from {file_path}...")
    
    if path.suffix.lower() == '.json':
        documents = load_json_file(file_path)
    elif path.suffix.lower() == '.csv':
        documents = load_csv_file(file_path)
    else:
        print(f"❌ Unsupported file format: {path.suffix}")
        print("   Supported: .json, .csv")
        return False
    
    print(f"   Found {len(documents)} resumes")
    
    # Validate required fields
    required_fields = ['id', 'name', 'job_title']
    for i, doc in enumerate(documents):
        for field in required_fields:
            if field not in doc:
                print(f"❌ Document {i} missing required field: {field}")
                return False
    
    print(f"\n📤 Uploading {len(documents)} resumes...")
    uploaded = upload_documents(endpoint, key, index_name, documents)
    print(f"\n✅ Upload complete: {uploaded}/{len(documents)} resumes")
    return uploaded > 0


def main():
    parser = argparse.ArgumentParser(
        description="Setup Azure AI Search for Talent Reconnect Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/setup_search.py                    # Create index only
    python scripts/setup_search.py --sample           # Create + sample data
    python scripts/setup_search.py --file resumes.json  # Upload from JSON
    python scripts/setup_search.py --file resumes.csv   # Upload from CSV

JSON format:
    [
      {"id": "1", "name": "John Doe", "email": "john@example.com", 
       "job_title": "ML Engineer", "experience_years": 5, 
       "location": "Dubai", "skills": ["Python", "TensorFlow"]}
    ]

CSV format:
    id,name,email,job_title,experience_years,location,skills
    1,John Doe,john@example.com,ML Engineer,5,Dubai,"Python,TensorFlow"
        """
    )
    parser.add_argument("--sample", action="store_true", 
                        help="Upload sample data for testing")
    parser.add_argument("--file", type=str, 
                        help="Upload resumes from JSON or CSV file")
    parser.add_argument("--skip-index", action="store_true",
                        help="Skip index creation (upload only)")
    args = parser.parse_args()
    
    print("\n🔧 Azure AI Search Setup for Talent Reconnect")
    print("=" * 50)
    
    endpoint, key, index_name = get_credentials()
    
    # Create index
    if not args.skip_index:
        if not create_index(endpoint, key, index_name):
            sys.exit(1)
    
    # Upload data
    if args.sample:
        upload_sample_data(endpoint, key, index_name)
    elif args.file:
        upload_from_file(endpoint, key, index_name, args.file)
    
    print("\n✅ Setup complete!")
    print(f"\nTest with: python chat.py")


if __name__ == "__main__":
    main()
