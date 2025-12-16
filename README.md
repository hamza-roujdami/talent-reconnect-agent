# Talent Reconnect Agent

AI-powered Talent Acquisition Agent using **Microsoft Agent Framework (MAF)** with **Azure AI Search** (100k resumes).

> ⚠️ **Demo purposes only** - Not intended for production use.

## Features

- 🔍 **Two Search Modes**: BM25 (keyword) and Semantic (neural reranking)
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
python chat.py                  # BM25 mode (default)
python chat.py --mode semantic  # Semantic mode (+15-25% relevance)
python main.py                  # API server on :8000
```

## Search Modes

| Mode | Command | How it Works | Best For |
|------|---------|--------------|----------|
| **BM25** | `--mode bm25` | Keyword matching (TF-IDF) | Exact skill matches |
| **Semantic** | `--mode semantic` | Neural reranking | Natural language queries |

### Example Comparison

```
Query: "Data Scientist Python Machine Learning Dubai"

BM25 Result #1:     Sunita Jones (3 yrs) - keyword match
Semantic Result #1: Hind Thompson (5 yrs, relevance: 3.04) - meaning match
```

Semantic search understands:
- "ML" = "Machine Learning"
- "UAE" ≈ "Dubai" ≈ "Gulf region"
- "build APIs" → finds "Backend Developer"

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    chat.py / main.py                            │
│                 (--mode bm25 | semantic)                        │
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
┌─────────────────────────┐       ┌─────────────────────────────┐
│   search_resumes_*()    │       │   send_outreach_email()     │
│                         │       │                             │
│  BM25: queryType=simple │       │  Personalized drafts        │
│  Semantic: queryType=   │       │  Candidate-specific         │
│    semantic + reranker  │       │                             │
└─────────────────────────┘       └─────────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│    Azure AI Search      │
│      100k resumes       │
│                         │
│  • Semantic config ✓    │
│  • BM25 + reranking     │
└─────────────────────────┘
```

## Project Structure

```
talent-reconnect-agent/
├── chat.py                 # Terminal chat (--mode bm25|semantic)
├── main.py                 # FastAPI server (:8000)
├── workflow.py             # Creates agent with selected search mode
├── config.py               # Environment configuration
├── agents/
│   └── factory.py          # Agent creation with search mode
├── tools/
│   ├── search_bm25.py      # BM25 search (Azure SDK)
│   ├── search_semantic.py  # Semantic search (Azure SDK)
│   └── email.py            # Outreach email drafts
├── instructions/
│   └── recruiter.md        # Agent system prompt
├── scripts/
│   ├── setup_search.py     # Create Azure AI Search index
│   ├── generate_resumes.py # Generate synthetic resumes
│   └── benchmark_search.py # Compare BM25 vs Semantic
└── static/
    └── index.html          # Web chat UI
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | Microsoft Agent Framework (MAF) |
| **LLM** | GPT-4.1 (OpenAI-compatible) |
| **Search** | Azure AI Search (100k docs) |
| **Search SDK** | `azure-search-documents` |
| **API** | FastAPI + SSE streaming |

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

### 1. Create Index with Semantic Config

```bash
python scripts/setup_search.py
```

Creates index with:
- Searchable fields (name, title, skills, summary)
- Filterable fields (experience_years, location)
- Semantic configuration for neural reranking

### 2. Generate & Upload Resumes

```bash
# Generate 100k synthetic resumes
python scripts/generate_resumes.py --count 100000 --upload
```

### 3. Benchmark Search Modes

```bash
python scripts/benchmark_search.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web chat UI |
| `/health` | GET | Health check |
| `/chat` | POST | Chat (non-streaming) |
| `/chat/stream` | POST | Chat (SSE streaming) |

## How Search Works

### BM25 (Keyword Matching)

```python
# tools/search_bm25.py
client.search(
    search_text="Python ML Engineer",
    # No query_type = defaults to BM25
)
```

- Matches exact keywords
- Scores by term frequency × document length
- Fast (~100ms)

### Semantic (Neural Reranking)

```python
# tools/search_semantic.py
client.search(
    search_text="Python ML Engineer",
    query_type=QueryType.SEMANTIC,
    semantic_configuration_name="default",
)
```

- BM25 first, then neural reranker
- Understands meaning and context
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
