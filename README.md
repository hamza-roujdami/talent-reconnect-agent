# Talent Reconnect Agent

AI-powered recruiting assistant using **Microsoft Foundry**. 

> ⚠️ **Demo purposes only** - Not intended for production use.

---

## Overview

Multi-agent recruiting workflow that helps find candidates, review interview history, and draft outreach emails.

```
User → Orchestrator → Specialist Agents → Azure AI Search
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator (TalentHub)                   │
│                  Routes requests to specialists                 │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌─────────────┐
│ RoleCrafter │ │ TalentScout │ │ InsightPulse │ │ ConnectPilot│
│  (profile)  │ │  (search)   │ │  (insights)  │ │  (outreach) │
└─────────────┘ └─────────────┘ └──────────────┘ └─────────────┘
                      │              │
                      ▼              ▼
              ┌─────────────┐ ┌─────────────┐
              │ Azure AI    │ │ Azure AI    │
              │ Search      │ │ Search      │
              │ (resumes)   │ │ (feedback)  │
              └─────────────┘ └─────────────┘
```

### Agents

| Agent | Key | Purpose |
|-------|-----|---------|
| **TalentHub** | `orchestrator` | Routes requests to specialists |
| **RoleCrafter** | `profile` | Defines job requirements |
| **TalentScout** | `search` | Finds candidates via Azure AI Search |
| **InsightPulse** | `insights` | Reviews interview feedback |
| **ConnectPilot** | `outreach` | Drafts personalized emails |

---

## Quick Start

```bash
# 1. Setup environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials

# 2. Create indexes and upload data
python data/01-create-index.py
python data/02-push-data.py --count 1000
python data/03-create-feedback-index.py
python data/04-push-feedback-data.py

# 3. Run tests
pytest tests/agents/ -v                           # Unit tests
PYTHONPATH=. python tests/e2e/test_workflow.py    # Full workflow
```

---

## Environment Variables

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |
| `FOUNDRY_MODEL_PRIMARY` | Model deployment (e.g., `gpt-4o-mini`) |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | Azure AI Search admin key |
| `SEARCH_RESUME_INDEX` | Resume index name (default: `resumes`) |
| `SEARCH_FEEDBACK_INDEX` | Feedback index name (default: `feedback`) |
| `USE_BUILTIN_SEARCH` | `true` for built-in search tool, `false` for FunctionTool |
| `AZURE_AI_SEARCH_CONNECTION_NAME` | Foundry connection name (if `USE_BUILTIN_SEARCH=true`) |

---

## Project Structure

```
talent-reconnect-agent/
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
│
├── agents/                   # Agent definitions
│   ├── factory.py            # AgentFactory class
│   ├── definitions.py        # Agent assembly with tools
│   ├── tools.py              # FunctionTool schemas
│   ├── orchestrator.py       # TalentHub + routing
│   ├── profile.py            # RoleCrafter agent
│   ├── search.py             # TalentScout agent
│   ├── insights.py           # InsightPulse agent
│   └── outreach.py           # ConnectPilot agent
│
├── tools/                    # Tool implementations
│   ├── search.py             # Candidate search
│   └── feedback.py           # Feedback lookup
│
├── static/
│   └── index.html            # Demo UI
│
├── tests/                    # Test suite
│   ├── conftest.py           # Shared fixtures
│   ├── agents/               # Agent tests
│   ├── tools/                # Tool tests
│   └── e2e/                  # End-to-end tests
│
├── data/                     # Azure AI Search setup
│   ├── 01-create-index.py    # Create resumes index
│   ├── 02-push-data.py       # Upload synthetic resumes
│   ├── 03-create-feedback-index.py
│   ├── 04-push-feedback-data.py
│   └── README.md
│
└── infra/                    # Bicep infrastructure (optional)
    ├── main.bicep            # Core AI resources
    ├── app-hosting.bicep     # Container Apps, APIM
    └── network-security.bicep
```

---

## Data Setup

Azure AI Search indexes for candidates and interview feedback:

```bash
# Create indexes (semantic search enabled)
python data/01-create-index.py
python data/03-create-feedback-index.py

# Upload synthetic data
python data/02-push-data.py --count 1000        # 1K resumes
python data/04-push-feedback-data.py            # Feedback for each

# Preview without uploading
python data/02-push-data.py --count 100 --dry-run
```

See [data/README.md](data/README.md) for details.

---

## Testing

```bash
# Unit tests (no Azure needed)
pytest tests/agents/test_routing.py -v

# Tool tests (needs Azure AI Search)
pytest tests/tools/ -v

# Full e2e workflow (needs Azure AI Foundry + Search)
PYTHONPATH=. python tests/e2e/test_workflow.py

# All tests
pytest tests/ -v
```

---

## Infrastructure (Optional)

Enterprise-grade Bicep templates in `infra/`:

- **Core AI**: AI Foundry, Cosmos DB, AI Search, Storage
- **App Hosting**: Container Apps, API Management, App Insights
- **Networking**: VNet, App Gateway + WAF, Private Endpoints

See [infra/README.md](infra/README.md) for deployment instructions.

---

## Usage Example

```python
import asyncio
from agents import AgentFactory

async def main():
    async with AgentFactory() as factory:
        # Direct agent call
        response = await factory.chat("Find Python developers in Dubai", "search")
        print(response)
        
        # Auto-routing
        response, agent = await factory.orchestrate("What feedback do we have on Ahmed?")
        print(f"Routed to: {agent}")
        print(response)

asyncio.run(main())
```
---