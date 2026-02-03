# Talent Reconnect Agent

AI-powered recruiting assistant using **Azure AI Foundry** and the **Responses API**.

> ⚠️ **Demo purposes only** - Not intended for production use.

---

## Overview

Multi-agent recruiting workflow that helps find candidates, review interview history, and draft outreach emails.

```
User → Orchestrator → Specialist Agents → Azure AI Search
```

**Features:**
- 🎯 Multi-agent orchestration with handoff routing
- 🔍 Semantic search across 100K+ resumes
- 📋 Interview feedback history
- ✉️ Personalized outreach emails
- 🌐 FastAPI server with SSE streaming
- 💾 Cosmos DB session persistence (with in-memory fallback)

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
| **RoleCrafter** | `profile` | Defines job requirements, generates candidate profile |
| **TalentScout** | `search` | Finds candidates via Azure AI Search |
| **InsightPulse** | `insights` | Reviews interview feedback |
| **ConnectPilot** | `outreach` | Drafts personalized emails |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Azure subscription with:
  - Azure AI Foundry project
  - Azure AI Search (Standard tier for semantic search)
  - Azure Cosmos DB (optional, for session persistence)

### Setup

```bash
# 1. Clone and setup environment
git clone https://github.com/your-org/talent-reconnect-agent.git
cd talent-reconnect-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Create search indexes and upload data
python data/01-create-index.py
python data/02-push-data.py --count 10000
python data/03-create-feedback-index.py
python data/04-push-feedback-data.py

# 4. (Optional) Setup Cosmos DB for session persistence
# Create database and container via Azure CLI:
az cosmosdb sql database create \
  --account-name <your-cosmos-account> \
  --resource-group <your-rg> \
  --name talent-reconnect

az cosmosdb sql container create \
  --account-name <your-cosmos-account> \
  --resource-group <your-rg> \
  --database-name talent-reconnect \
  --name sessions \
  --partition-key-path "/session_id"

# Grant yourself data-plane RBAC (Cosmos DB Data Contributor):
az cosmosdb sql role assignment create \
  --account-name <your-cosmos-account> \
  --resource-group <your-rg> \
  --role-definition-id "00000000-0000-0000-0000-000000000002" \
  --principal-id $(az ad signed-in-user show --query id -o tsv) \
  --scope "/"

# 5. Run the app
python main.py
# Open http://localhost:8000
```

> **Note:** If Cosmos DB is not configured, the app falls back to in-memory session storage (sessions lost on restart).

---

## Infrastructure Deployment

Two deployment options in `infra/`:

| Mode | Folder | Description |
|------|--------|-------------|
| **🌐 Public** | `infra/public/` | All public endpoints - fast, simple, great for demos |
| **🔒 Private** | `infra/private/` | VNet + Private Endpoints + WAF - enterprise-ready |

### Public (Recommended for Demos)

```bash
cd infra/public
./deploy.sh rg-talent-reconnect swedencentral
```

Deploys: AI Foundry, AI Search, Cosmos DB, Container Apps, APIM, App Insights

### Private (Enterprise)

```bash
cd infra/private
az deployment group create -g rg-talent-reconnect -f main.bicep -p main.bicepparam
az deployment group create -g rg-talent-reconnect -f network-security.bicep -p network-security.bicepparam
az deployment group create -g rg-talent-reconnect -f app-hosting.bicep -p app-hosting.bicepparam
```

Adds: VNet, Private Endpoints, App Gateway + WAF, NSGs

See [infra/README.md](infra/README.md) for full details.

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
| `COSMOS_ENDPOINT` | Cosmos DB endpoint (optional) |

---

## Project Structure

```
talent-reconnect-agent/
├── main.py                   # FastAPI server entry point
├── config.py                 # Environment configuration
├── requirements.txt          # Python dependencies
│
├── agents/                   # Agent definitions
│   ├── factory.py            # AgentFactory class
│   ├── definitions.py        # Agent assembly with tools
│   ├── orchestrator.py       # TalentHub + routing
│   ├── profile_agent.py      # RoleCrafter agent
│   ├── search_agent.py       # TalentScout agent
│   ├── insights_agent.py     # InsightPulse agent
│   └── outreach_agent.py     # ConnectPilot agent
│
├── tools/                    # Tool implementations
│   ├── search_provider.py    # Candidate search (Azure AI Search)
│   └── feedback_lookup.py    # Feedback lookup
│
├── api/                      # API routes
│   └── routes.py             # FastAPI routes with SSE streaming
│
├── sessions/                 # Session persistence
│   └── cosmos_store.py       # Cosmos DB + in-memory fallback
│
├── static/
│   └── index.html            # Demo UI
│
├── data/                     # Azure AI Search setup
│   ├── 01-create-index.py    # Create resumes index
│   ├── 02-push-data.py       # Upload synthetic resumes
│   ├── 03-create-feedback-index.py
│   ├── 04-push-feedback-data.py
│   └── README.md
│
├── infra/                    # Azure infrastructure
│   ├── public/               # Public endpoints (demo)
│   ├── private/              # Private networking (enterprise)
│   └── README.md
│
├── evals/                    # Evaluation suite
│   ├── golden_dataset.json   # Test cases
│   └── test_*.py             # Evaluation tests
│
└── tests/                    # Test suite
    ├── conftest.py
    └── test_*.py
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

## Demo Workflow

1. **Define Role**: "Senior AI Engineer in Dubai"
   - RoleCrafter generates a candidate profile immediately

2. **Search Candidates**: "yes" (confirms profile)
   - TalentScout searches 100K+ resumes

3. **Check History**: "Check feedback for candidate 1"
   - InsightPulse retrieves interview history

4. **Draft Outreach**: "Send email to candidate 1"
   - ConnectPilot drafts personalized email

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Specific test files
pytest tests/test_agents.py -v
pytest tests/test_api.py -v
```

---

## Infrastructure (Optional)

Enterprise-grade Bicep templates in `infra/`:

- **Public Mode** (`infra/public/`): AI Foundry, Cosmos DB, AI Search, Container Apps, APIM
- **Private Mode** (`infra/private/`): + VNet, App Gateway + WAF, Private Endpoints

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

## License

MIT License - Demo purposes only.