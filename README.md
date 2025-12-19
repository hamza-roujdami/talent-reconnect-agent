# Talent Reconnect Agent

AI-powered Talent Acquisition Agent using **Microsoft Agent Framework (MAF)** with **Azure AI Search** (100k resumes).

> ⚠️ **Demo purposes only** - Not intended for production use.

## Features

- 🔍 **Semantic Search**: BM25 + Neural reranking + Scoring profiles
- 👥 **100,000 Resumes** in Azure AI Search
- 🤖 **Human-in-the-Loop**: Agent pauses for approval at each step
- ✉️ **Email Drafting**: Personalized outreach generation (demo only, no actual emails sent)

## Quick Start

```bash
# 1. Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials

# 2. Run
python chat.py                  # Terminal chat
python main.py                  # API server on :8000
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    chat.py / main.py                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Recruiter Agent                            │
│              (Human-in-the-Loop workflow)                       │
│                                                                 │
│  Step 1: Understand requirements                                │
│  Step 2: Generate Job Description → User approves               │
│  Step 3: Search Candidates        → User selects                │
│  Step 4: Draft Outreach           → User approves               │
└─────────────────────────────────────────────────────────────────┘
            │                                   │
            ▼                                   ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│ search_resumes_semantic()   │   │   send_outreach_email()     │
│                             │   │                             │
│  • BM25 retrieval           │   │  Personalized drafts        │
│  • Scoring profile boost    │   │  Candidate-specific         │
│  • Semantic reranking       │   │                             │
│  • Custom match scoring     │   │                             │
└─────────────────────────────┘   └─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│    Azure AI Search          │
│      100k resumes           │
│                             │
│  • Semantic ranker ✓        │
│  • Scoring profiles ✓       │
│  • Synonyms ✓               │
│  • Facets ✓                 │
└─────────────────────────────┘
```

## Project Structure

```
talent-reconnect-agent/
├── chat.py                 # Terminal chat
├── main.py                 # FastAPI server (:8000)
├── config.py               # Environment configuration
├── agents/
│   └── factory.py          # create_recruiter() agent
├── tools/
│   ├── search_semantic.py  # Semantic search (BM25 + Reranker)
│   ├── scoring.py          # Custom match scoring
│   └── email.py            # Outreach email drafts
├── instructions/
│   └── recruiter.md        # Agent system prompt
├── api/
│   └── routes.py           # /chat endpoint with streaming
├── static/
│   └── index.html          # Web chat UI
├── tools/azure-ai-search/  # Learning scripts
│   ├── 00-overview.md      # Concepts guide
│   ├── 01-create-index.py  # Create index schema
│   ├── 02-push-data.py     # Generate & upload resumes
│   └── 03-search.py        # Search methods demo
└── evals/
    ├── golden_dataset.json # Test queries and expectations
    ├── test_search_quality.py
    ├── test_agent_behavior.py
    └── test_e2e_scenarios.py
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | Microsoft Agent Framework (MAF) |
| **LLM** | Azure OpenAI (gpt-4o) |
| **Search** | Azure AI Search (100k docs) |
| **Search SDK** | `azure-search-documents` |
| **API** | FastAPI + SSE streaming |

## Azure AI Search Features

| Feature | How We Use It | Benefit |
|---------|---------------|---------|
| **Semantic Ranking** | `query_type=QueryType.SEMANTIC` | Neural reranker understands meaning - "ML" matches "Machine Learning" |
| **Scoring Profiles** | `scoring_profile="talent-boost"` | Boost title 2x, skills 1.5x, experience for better ranking |
| **Synonyms** | `talent-synonyms` map | ML → Machine Learning, K8s → Kubernetes auto-expanded |
| **Facets** | `facets=["location", "current_title"]` | Shows candidate pool distribution (50 in Dubai, 30 in AD) |
| **Semantic Configuration** | `semantic_configuration_name="default"` | Prioritizes title, skills, summary fields |
| **JD-Based Search** | `job_description` parameter | Understands role context - "startup", "collaborate with ML team" |
| **Field Selection** | `select=["name", "skills", ...]` | Return only needed fields - reduces latency |
| **Filtering** | `filter="experience_years ge 3"` | Pre-filter results before ranking |

### Search Architecture

```
User Query: "Senior Python ML Engineer in Dubai with 5+ years"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Azure AI Search                          │
├─────────────────────────────────────────────────────────────┤
│  1. FILTER STAGE                                            │
│     └─ experience_years >= 5 (removes ~60% of docs)         │
├─────────────────────────────────────────────────────────────┤
│  2. BM25 RETRIEVAL                                          │
│     └─ Keyword match: Python, ML, Engineer, Dubai           │
│     └─ Returns top 50 candidates (configurable)             │
├─────────────────────────────────────────────────────────────┤
│  3. SEMANTIC RERANKING (if enabled)                         │
│     └─ Neural model scores each result by MEANING           │
│     └─ Understands context: "ML" = "Machine Learning"       │
│     └─ Returns top_k with @search.reranker_score            │
├─────────────────────────────────────────────────────────────┤
│  4. FIELD PROJECTION                                        │
│     └─ Returns: name, title, skills, experience, location   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              Application-Level Scoring
         (skills match %, experience fit, location)
```

## Environment Variables

```env
# LLM (OpenAI-compatible endpoint)
COMPASS_API_KEY=your-api-key
COMPASS_BASE_URL=https://api.core42.ai/v1
COMPASS_MODEL=gpt-4.1

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-admin-key
AZURE_SEARCH_INDEX=resumes
```

## Data Setup

### 1. Create Index

```bash
cd tools/azure-ai-search
python 01-create-index.py --dry-run  # Preview
python 01-create-index.py            # Create
```

### 2. Generate & Upload Resumes

```bash
python 02-push-data.py --count 100000
```

### 3. Test Search

```bash
python 03-search.py --method semantic --query "ML Engineer Dubai"
python 03-search.py --method facets --query "Data Engineer"
python 03-search.py --reference  # OData filter syntax
```

### Semantic Understanding

The search understands:
- "ML" = "Machine Learning"
- "UAE" ≈ "Dubai" ≈ "Gulf region"
- "build APIs" → finds "Backend Developer"

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web chat UI |
| `/health` | GET | Health check |
| `/chat` | POST | Chat (non-streaming) |
| `/chat/stream` | POST | Chat (SSE streaming) |

## How Search Works

### Semantic Search (BM25 + Neural Reranking)

```python
# tools/search_semantic.py
client.search(
    search_text="Python ML Engineer",
    query_type=QueryType.SEMANTIC,
    semantic_configuration_name="default",
    scoring_profile="talent-boost",  # Custom relevance boost
    facets=["location", "current_title"],  # Aggregated counts
)
```

**Pipeline:**
1. **BM25** - Keyword matching (retrieval)
2. **Scoring Profile** - Boost title 2x, skills 1.5x, experience
3. **Semantic Reranker** - Neural model reorders by meaning
4. **Synonyms** - ML → Machine Learning auto-expanded
5. **Custom Scoring** - `compute_match_score()` for final ranking

**Features:**
- Understands meaning and context
- Facets show candidate pool distribution
- Synonyms handle abbreviations (ML, AI, K8s)
- +15-25% relevance improvement
- Slightly slower (~160ms)

## Demo Flow

```
User: "I need a Python ML engineer in Dubai"

Agent: "What experience level and specific skills?"

User: "5+ years, PyTorch, production ML"

Agent: 📝 Here's a draft job description...
       "Does this look good?"

User: "yes"

Agent: 🔧 search_resumes_semantic()
       📊 Found 5 candidates:
       1. Hind Thompson (5 yrs) - Amazon AWS
       2. Chen Huang (4 yrs) - Stripe
       ...
       "Which candidates should I contact?"

User: "1 and 2"

Agent: 🔧 send_outreach_email()
       ✉️ Draft emails ready...
       "Shall I send these?"
```

## License

MIT
