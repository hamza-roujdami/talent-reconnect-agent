# Azure AI Search Setup

Scripts to create and populate the Azure AI Search indexes and Foundry IQ Knowledge Bases.

## Prerequisites

- Azure subscription with an AI Search service (Standard tier for semantic search)
- Python 3.9+ with dependencies: `pip install -r requirements.txt`

Set these in your `.env`:

```bash
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-admin-key
```

## Quick Start

```bash
# 1. Create the resumes index
python data/01-create-index.py

# 2. Generate and upload synthetic resumes
python data/02-push-data.py --count 1000

# 3. Create the feedback index
python data/03-create-feedback-index.py

# 4. Generate and upload interview feedback
python data/04-push-feedback-data.py

# 5. Create Foundry IQ Knowledge Sources and Bases
pip install azure-search-documents==11.7.0b2
python data/09-create-knowledge-bases.py

# 6. Create MCP connections in Foundry (requires PROJECT_RESOURCE_ID)
python data/10-create-mcp-connections.py
```

## Scripts

| Script | Purpose |
|--------|---------|
| `01-create-index.py` | Creates `resumes` index with semantic config |
| `02-push-data.py` | Generates synthetic resumes using Faker |
| `03-create-feedback-index.py` | Creates `feedback` index linked to resumes via `candidate_id` |
| `04-push-feedback-data.py` | Generates interview feedback for existing candidates |
| `09-create-knowledge-bases.py` | Creates Foundry IQ knowledge sources and bases |
| `10-create-mcp-connections.py` | Creates MCP project connections for agent access |

## Options

```bash
# Preview without uploading
python data/02-push-data.py --count 100 --dry-run

# Control feedback volume
python data/04-push-feedback-data.py --total-feedback 5000 --dry-run
```

## Configuration

Set these in your `.env` for Foundry IQ:

```bash
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
RESUMES_KB_NAME=resumes-kb
FEEDBACK_KB_NAME=feedback-kb
RESUMES_KB_CONNECTION=resumes-kb-mcp
FEEDBACK_KB_CONNECTION=feedback-kb-mcp
```

## Index Configuration

Both indexes use Microsoft's built-in semantic ranker (no vector embeddings needed):

- **Semantic config**: `default`
- **Source URL**: `source_url` field for citations
- **Query type**: `SEMANTIC` for intelligent ranking
