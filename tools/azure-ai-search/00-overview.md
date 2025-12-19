# Azure AI Search - From Scratch Guide

## Prerequisites

Before starting, you need:

| Requirement | How to Get It |
|-------------|---------------|
| **Azure Subscription** | [Free account](https://azure.microsoft.com/free/) |
| **Azure AI Search Service** | [Create in Portal](https://portal.azure.com/#create/Microsoft.Search) |
| **Python 3.9+** | `brew install python` or [python.org](https://python.org) |
| **Azure SDK** | `pip install azure-search-documents` |

### Create Azure AI Search Service

```bash
# Option 1: Azure Portal
# Go to: portal.azure.com → Create a resource → "Azure AI Search"

# Option 2: Azure CLI
az search service create \
    --name my-search-service \
    --resource-group my-rg \
    --sku Basic \
    --location uaenorth
```

### Get Your Credentials

After creating the service, grab these from the Azure Portal:

```bash
# Azure Portal → Your Search Service → Settings → Keys
AZURE_SEARCH_ENDPOINT=https://<your-service>.search.windows.net
AZURE_SEARCH_KEY=<your-admin-key>
```

### Sample Data (100k+ Resumes)

The resume data is **synthetic** - generated using the Faker library. 

```bash
# Generate 1,000 resumes (dry run - preview only)
python 02-push-data.py --count 1000 --dry-run

# Generate and upload 100,000 resumes to Azure AI Search
python 02-push-data.py --count 100000
```

**What the generator creates:**
- Realistic names (multi-locale: US, UK, AU, India, UAE)
- Job titles (Engineering, Data, Product, Design, Management)
- Skills pools (Programming, Frontend, Backend, Cloud, Data, ML)
- Companies (Tech giants, Consulting, UAE companies, Startups)
- Locations (Dubai, Abu Dhabi, Remote, etc.) - 50% UAE weighted
- Experience years, education, certifications
- `open_to_opportunities` flag
- ML-specific flags (ml_production, genai_experience, etc.)

> 📁 See [`02-push-data.py`](02-push-data.py) for the full generator.

---

## The Big Picture

Azure AI Search has **4 main stages** you need to understand:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AZURE AI SEARCH PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. INDEXING          2. DATA IMPORT       3. RETRIEVAL      4. RANKING    │
│  ─────────────        ──────────────       ───────────       ─────────     │
│  Define schema        Load documents       Query the         Order results │
│  (what fields?)       (push or pull?)      index             (by relevance)│
│                                                                             │
│  ┌──────────┐        ┌──────────┐         ┌──────────┐      ┌──────────┐  │
│  │  Index   │◀───────│  Data    │         │  Query   │─────▶│ Results  │  │
│  │  Schema  │        │  Source  │         │  Engine  │      │ Ranked   │  │
│  └──────────┘        └──────────┘         └──────────┘      └──────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: INDEX (Schema Definition)

**Question: "What does my data look like?"**

An index is like a database table schema. You define:
- Field names
- Field types (string, int, collection, vector)
- Field behaviors (searchable, filterable, sortable, facetable)

```
Example: Resume Index Schema
┌─────────────────────────────────────────────────────────────┐
│ Field Name        │ Type              │ Behaviors          │
├───────────────────┼───────────────────┼────────────────────┤
│ id                │ Edm.String        │ key                │
│ name              │ Edm.String        │ searchable         │
│ skills            │ Collection(String)│ searchable,filter  │
│ experience_years  │ Edm.Int32         │ filterable,sortable│
│ location          │ Edm.String        │ searchable,filter  │
│ summary           │ Edm.String        │ searchable         │
│ embedding         │ Collection(Single)│ vector search      │
└─────────────────────────────────────────────────────────────┘
```

**Key Decisions:**
- Which fields should be **searchable**? (full-text search)
- Which fields should be **filterable**? (WHERE clauses)
- Which fields should be **sortable**? (ORDER BY)
- Do you need **vectors**? (semantic similarity)

---

## Stage 2: DATA IMPORT (Loading Documents)

**Question: "How do I get my data into the index?"**

Two methods:

### Option A: PUSH Model (Your Code Uploads)
```
Your App ──────▶ Azure Search API ──────▶ Index
         (POST /indexes/{name}/docs)
```
- **You control** when and what to upload
- Works with **any data source**
- Best for: real-time sync, custom sources

### Option B: PULL Model (Indexer Fetches)
```
Azure Indexer ──────▶ Data Source ──────▶ Index
              (scheduled crawl)
```
- Azure **automatically** crawls your data
- Works with: Blob Storage, SQL, Cosmos DB, SharePoint
- Best for: bulk data, scheduled updates

**Actions:**
- `upload` - Insert new or replace existing
- `merge` - Update existing fields only
- `mergeOrUpload` - Merge if exists, upload if new
- `delete` - Remove document

---

## Stage 3: RETRIEVAL (Finding Documents)

**Question: "How do I find matching documents?"**

### Retrieval Methods:

| Method | How It Works | Use Case |
|--------|--------------|----------|
| **Full-text** | Keyword matching (BM25) | "Python developer" |
| **Vector** | Embedding similarity | "Find similar resumes" |
| **Hybrid** | Both combined (RRF) | Best accuracy |
| **Filter** | Exact match on fields | `location eq 'Dubai'` |

```python
# Full-text retrieval
search_text="Senior ML Engineer"

# Vector retrieval  
vector_queries=[VectorizedQuery(vector=embedding, fields="embedding")]

# Hybrid (both)
search_text="ML Engineer" + vector_queries=[...]

# With filter
filter="experience_years ge 5"
```

---

## Stage 4: RANKING (Ordering Results)

**Question: "In what order should results appear?"**

### Ranking Layers:

```
Retrieved Documents (e.g., 100 matches)
           │
           ▼
    ┌──────────────┐
    │  BM25 Score  │  ← Default relevance scoring
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │  RRF Fusion  │  ← If hybrid (combines BM25 + vector)
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │  Semantic    │  ← Optional: LLM re-ranks top 50
    │  Ranker      │
    └──────────────┘
           │
           ▼
    Top N Results
```

### Ranking Options:

| Ranker | What It Does | Cost |
|--------|--------------|------|
| **BM25** | Term frequency scoring | Free |
| **Vector** | Cosine similarity | Free |
| **RRF** | Merges BM25 + Vector scores | Free |
| **Semantic** | LLM re-ranks by meaning | Paid tier |
| **Scoring Profile** | Custom boosts (freshness, etc.) | Free |

---

## What Your App Currently Uses

```
┌────────────────────────────────────────────────────────────────┐
│ talent-reconnect-agent                                         │
├────────────────────────────────────────────────────────────────┤
│ 1. INDEX        │ Pre-existing "resumes" index                 │
│ 2. DATA IMPORT  │ (already populated)                          │
│ 3. RETRIEVAL    │ Full-text search (JD as query)               │
│ 4. RANKING      │ BM25 → Semantic Ranker                       │
│ 5. POST-PROCESS │ Your compute_match_score() function          │
└────────────────────────────────────────────────────────────────┘
```

---

## Files in This Folder

| File | Purpose | Run It |
|------|---------|--------|
| `00-overview.md` | This guide - concepts & pipeline | - |
| `01-create-index.py` | Create index schema (educational) | `python 01-create-index.py --dry-run` |
| `02-push-data.py` | Generate & upload resumes | `python 02-push-data.py --count 1000` |
| `03-search.py` | All search methods + enhancements | `python 03-search.py --help` |

### 03-search.py Features

**Search Methods:**
```bash
python 03-search.py --method fulltext   # BM25 keyword search
python 03-search.py --method filter      # OData filter queries
python 03-search.py --method semantic    # BM25 + Semantic reranker
python 03-search.py --method combined    # Semantic + filters (production)
```

**Enhancements:**
```bash
python 03-search.py --method facets      # Aggregated counts for UI
python 03-search.py --method synonyms    # Setup ML → Machine Learning
python 03-search.py --method scoring     # Custom relevance boosting
python 03-search.py --reference          # OData filter syntax guide
```
