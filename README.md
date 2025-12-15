# Talent Reconnect Agent

AI-powered Talent Acquisition Agent using **Microsoft Agent Framework (MAF)** with **Azure AI Search** (100k+ resumes).

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

# 4. Run
python main.py          # API server on :8000 (includes web UI)
python chat.py          # Terminal chat

# 5. Test in browser
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

The agent searches 100k+ resumes stored in **Azure AI Search** (UAE North region).

**Required Index Schema:**
```
Index: resumes
Fields:
  - name (string, searchable)
  - email (string)
  - job_title (string, searchable)
  - experience_years (int32, filterable)
  - location (string, searchable, filterable)
  - skills (Collection<string>, searchable, filterable)
```

**To create your own index:**
1. Create an Azure AI Search service in Azure Portal
2. Create an index named `resumes` with the schema above
3. Upload your resume data (JSON format)
4. Add the endpoint and key to `.env`
