# Talent Reconnect Agent

AI-powered Talent Acquisition Agent using **Microsoft Agent Framework (MAF)** with **Azure AI Search** (100k+ resumes).

## Prerequisites

- **Azure Subscription** - [Create one free](https://azure.microsoft.com/free/)
- **Azure AI Search** - Basic tier or higher ([Create service](https://portal.azure.com/#create/Microsoft.Search))
- **LLM Access** - One of:
  - [Microsoft Foundry](https://ai.azure.com/) (Azure OpenAI)
  - [Compass API](https://core42.ai/) (GPT-4.1)
  - Any OpenAI-compatible endpoint

## Quick Start

```bash
# 1. Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Setup Azure AI Search (create index + load 100k resumes)
python scripts/setup_search.py                           # Create index
python scripts/generate_resumes.py --count 100000 --upload  # Generate & upload resumes

# 5. Run
python main.py          # API server on :8000 (includes web UI)
python chat.py          # Terminal chat

# 6. Test in browser
open http://localhost:8000   # Web chat UI
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User (Web/CLI)                          │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Server (:8000)                     │
│                    /chat  /chat/stream  /session                │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Recruiter Agent                           │
│              (Human-in-the-Loop workflow)                       │
│                                                                 │
│  Step 1: Generate Job Description  → User approves/edits        │
│  Step 2: Search Candidates         → User selects candidates    │
│  Step 3: Draft Outreach            → User approves emails       │
└─────────────────────────────────────────────────────────────────┘
            │                                   │
            ▼                                   ▼
┌─────────────────────────┐       ┌─────────────────────────────┐
│   search_resumes()      │       │   send_outreach_email()     │
│                         │       │                             │
│  • Full-text search     │       │  • Personalized drafts      │
│  • Skills matching      │       │  • Candidate-specific       │
│  • Experience filter    │       │  • Company branding         │
│  • Location filter      │       │                             │
└─────────────────────────┘       └─────────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│    Azure AI Search      │
│      (UAE North)        │
│                         │
│  • 100k+ resumes        │
│  • Lucene full-text     │
│  • OData filters        │
└─────────────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | Microsoft Agent Framework (MAF) | Single-agent orchestration |
| **LLM** | GPT-4.1 via Compass API | Language model |
| **Search** | Azure AI Search | 100k+ resume corpus (UAE North) |
| **API Server** | FastAPI + Uvicorn | REST API with SSE streaming |
| **HTTP Client** | httpx | Async HTTP for search queries |

## Demo Flow

```
User: "AI Engineer"
  ↓
Agent: Generates job description → "Modify or proceed?"
  ↓
User: "ok"
  ↓
Agent: 🔧 search_resumes → Shows candidate table → "Who to contact?"
  ↓
User: "William and Nicole"
  ↓
Agent: 🔧 send_outreach_email → Shows email drafts → "Send?"
  ↓
User: "yes"
  ↓
Agent: "Emails ready! Good luck with hiring!"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web chat UI |
| `/health` | GET | Health check |
| `/chat` | POST | Chat (non-streaming) |
| `/chat/stream` | POST | Chat (SSE streaming) |
| `/session/{id}` | GET | Get session history |

## Project Structure

```
talent-reconnect-agent/
├── main.py                 # Entry point (FastAPI server)
├── chat.py                 # Terminal chat CLI
├── config.py               # Environment configuration
├── workflow.py             # Returns Recruiter agent
├── agents/
│   └── factory.py          # Agent creation
├── api/
│   └── routes.py           # REST endpoints
├── instructions/
│   └── recruiter.md        # Agent system prompt
├── tools/
│   ├── search.py           # Azure AI Search
│   └── email.py            # Outreach drafts
├── static/
│   └── index.html          # Web chat UI
└── .env.example            # Environment template
```

## Environment Variables

```env
# LLM (Compass API)
COMPASS_API_KEY=your-api-key
COMPASS_BASE_URL=https://api.core42.ai/v1
COMPASS_MODEL=gpt-4.1

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-admin-key
AZURE_SEARCH_INDEX=resumes
```


## Data Setup (Azure AI Search)

The agent searches resumes stored in **Azure AI Search**.

### Quick Setup (with sample data)

```bash
# Install dependency
pip install azure-search-documents

# Create index + upload 10 sample resumes
python scripts/setup_search.py --sample
```

### Full Setup (with your own data)

**Step 1: Create Azure AI Search Service**
```bash
# Create resource group
az group create --name talent-reconnect-rg --location uaenorth

# Create search service (basic tier for production, free for testing)
az search service create \
  --name your-search-service \
  --resource-group talent-reconnect-rg \
  --location uaenorth \
  --sku basic

# Get admin key
az search admin-key show \
  --service-name your-search-service \
  --resource-group talent-reconnect-rg
```

**Step 2: Configure Environment**
```bash
# Add to .env
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-admin-key
AZURE_SEARCH_INDEX=resumes
```

**Step 3: Create Index & Upload Data**
```bash
# Create index only
python scripts/setup_search.py

# Upload from JSON file
python scripts/setup_search.py --file resumes.json

# Upload from CSV file
python scripts/setup_search.py --file resumes.csv
```

### Generate Synthetic Data (100k+ resumes)

Don't have resume data? Generate realistic synthetic resumes using Faker:

```bash
# Install dependencies
pip install faker pandas

# Generate 1,000 resumes (default)
python scripts/generate_resumes.py

# Generate 100,000 resumes
python scripts/generate_resumes.py --count 100000 --output resumes.json

# Generate and upload directly to Azure AI Search
python scripts/generate_resumes.py --count 100000 --upload

# Use a seed for reproducible data
python scripts/generate_resumes.py --count 50000 --seed 42
```

The generator creates diverse resumes with:
- **Job titles**: Engineering, Data Science, Product, Design, Management
- **Skills**: Relevant to job category (ML engineers get PyTorch, DevOps gets Kubernetes, etc.)
- **Locations**: Weighted towards UAE/GCC (Dubai 25%, Abu Dhabi 15%, etc.)
- **Experience**: Realistic distribution (1-20 years)

### Data Format

**JSON:**
```json
[
  {
    "id": "1",
    "name": "Ahmed Hassan",
    "email": "ahmed@example.com",
    "job_title": "Senior ML Engineer",
    "experience_years": 6,
    "location": "Dubai, UAE",
    "skills": ["Python", "TensorFlow", "Azure"]
  }
]
```

**CSV:**
```csv
id,name,email,job_title,experience_years,location,skills
1,Ahmed Hassan,ahmed@example.com,Senior ML Engineer,6,Dubai UAE,"Python,TensorFlow,Azure"
```

### Index Schema

| Field | Type | Searchable | Filterable |
|-------|------|------------|------------|
| id | string (key) | - | - |
| name | string | ✅ | - |
| email | string | - | - |
| job_title | string | ✅ | - |
| experience_years | int32 | - | ✅ |
| location | string | ✅ | ✅ |
| skills | Collection(string) | ✅ | ✅ |

---

## How Azure AI Search Works

End-to-end pipeline from service creation to search results:

### Step 1: Create Search Service

```bash
# Azure Portal or CLI
az search service create --name your-service --resource-group your-rg --sku basic
```

**Output:** `https://your-service.search.windows.net` + Admin Key

### Step 2: Create Index (Schema Definition)

```python
# scripts/setup_search.py defines the schema
fields = [
    SimpleField(name="id", type="Edm.String", key=True),
    SearchableField(name="name"),           # Full-text search enabled
    SearchableField(name="job_title"),      # Full-text search enabled
    SearchableField(name="skills", collection=True, filterable=True),
    SearchableField(name="location", filterable=True),
    SimpleField(name="experience_years", type="Edm.Int32", filterable=True),
]
```

- **Searchable** = Field is tokenized for full-text search
- **Filterable** = Field supports exact matching, ranges, comparisons

### Step 3: Generate Data

```bash
python scripts/generate_resumes.py --count 100000
```

Creates JSON array with 100k synthetic resumes using Faker library.

### Step 4: Upload & Index Documents

```bash
python scripts/generate_resumes.py --count 100000 --upload
```

**What happens internally:**
1. Documents sent in batches (1000 at a time)
2. Azure AI Search **tokenizes** searchable text fields:
   - `"Senior ML Engineer"` → `["senior", "ml", "engineer"]`
3. Creates **inverted index** for fast lookup:
   - `"python"` → `[doc1, doc5, doc99, doc234, ...]`
4. Stores filterable fields in columnar format

> ⚠️ **No embeddings** - This setup uses **keyword/full-text search**, not vector search

### Step 5: Query/Search

```python
# tools/search.py
async def search_resumes(query: str, ...) -> str:
    params = {
        "search": query,              # Full-text search
        "filter": "experience_years ge 5",  # OData filter
        "top": 10,
        "select": "name,email,job_title,skills,location"
    }
    response = await client.post(search_url, json=params)
```

**Query types:**
- **Full-text:** `search="machine learning engineer"` → Matches docs containing those terms
- **Filters:** `filter="experience_years ge 5 and location eq 'Dubai'"` → Exact filtering
- **Combined:** Both together for precise results

### Step 6: Results Returned

```json
{
  "value": [
    {
      "@search.score": 8.234,
      "name": "Ahmed Hassan",
      "job_title": "Senior Data Engineer",
      "skills": ["Python", "Spark", "Azure"],
      "experience_years": 6,
      "location": "Dubai, UAE"
    }
  ]
}
```

- **@search.score** = Relevance score using BM25 algorithm (term frequency + doc length)

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Searchable** | Field is tokenized & indexed for full-text search |
| **Filterable** | Field supports exact matching, ranges, comparisons |
| **BM25 Scoring** | Default ranking algorithm (term frequency + doc length) |
| **Inverted Index** | Maps terms → document IDs for fast lookup |
| **Keyword Search** | This setup uses text matching, not vector/semantic search |
