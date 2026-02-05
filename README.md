# Talent Reconnect Agent

AI-powered recruiting assistant built on **Azure AI Foundry** with multi-agent orchestration.

> ⚠️ **Demo purposes only** - Not intended for production use.

## Overview

6-agent recruiting system that routes conversations intelligently:

```
User → Orchestrator → Specialist Agent → Tools (Search, Email, Web)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestrator                            │
│     Routes requests • Handles greetings • Rejects off-topic     │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │              │
         ▼              ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐
│ RoleCrafter │ │ TalentScout │ │ InsightPulse │ │ ConnectPilot│ │ MarketRadar │
│  (profile)  │ │  (search)   │ │  (feedback)  │ │  (outreach) │ │  (research) │
└─────────────┘ └─────────────┘ └──────────────┘ └─────────────┘ └─────────────┘
                      │              │              │              │
                      ▼              ▼              ▼              ▼
              ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
              │ Foundry IQ  │ │ Foundry IQ  │ │  SendEmail  │ │ WebSearch   │
              │ resumes-kb  │ │ feedback-kb │ │  Function   │ │ Tool        │
              │ (MCPTool)   │ │ (MCPTool)   │ │             │ │             │
              └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Agents

| Agent | Key | Purpose | Tools |
|-------|-----|---------|-------|
| **Orchestrator** | `orchestrator` | Routes requests, handles greetings, rejects off-topic | None |
| **RoleCrafter** | `role-crafter` | Builds job profiles and gathers requirements | None |
| **TalentScout** | `talent-scout` | Searches 100k+ resumes | Foundry IQ (MCPTool) |
| **InsightPulse** | `insight-pulse` | Reviews interview feedback history | Foundry IQ (MCPTool) |
| **ConnectPilot** | `connect-pilot` | Drafts and sends outreach emails | FunctionTool |
| **MarketRadar** | `market-radar` | Researches salaries, trends, companies | WebSearchPreviewTool |

## Tech Stack

| Component | Technology |
|-----------|------------|
| **SDK** | Azure AI Foundry v2 (`azure-ai-projects>=2.0.0b3`, `azure-ai-agents>=1.0.0b1`) |
| **Multi-Agent** | Foundry Agents with Responses API |
| **Model** | `gpt-4o-mini` via Foundry |
| **Knowledge Search** | Foundry IQ Knowledge Bases via `MCPTool` |
| **Web Research** | `WebSearchPreviewTool` |
| **Memory** | Azure AI Foundry Memory Store (cross-session) |
| **Sessions** | Azure Cosmos DB (falls back to in-memory) |
| **API** | FastAPI with SSE streaming |

> 📚 [Get started with Azure AI Foundry SDK](https://learn.microsoft.com/en-us/azure/ai-foundry/quickstarts/get-started-code)

---

## Getting Started

### 1. Clone and Install

```bash
git clone https://github.com/your-org/talent-reconnect-agent.git
cd talent-reconnect-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your Azure credentials:

```bash
# Azure AI Foundry
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
FOUNDRY_MODEL_PRIMARY=gpt-4o-mini

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-admin-key

# Foundry IQ Knowledge Bases
RESUMES_KB_NAME=resumes-kb
FEEDBACK_KB_NAME=feedback-kb
RESUMES_KB_CONNECTION=resumes-kb-mcp
FEEDBACK_KB_CONNECTION=feedback-kb-mcp

# Optional
ENABLE_WEB_SEARCH=true
ENABLE_MEMORY=true
```

### 3. Provision Azure Infrastructure

You need:
- **Azure AI Foundry project** - [Create in Azure Portal](https://portal.azure.com)
- **Azure AI Search** (Standard tier for semantic search)
- **Azure Cosmos DB** (optional, for session persistence)

For MCP connections, also set:
```bash
PROJECT_RESOURCE_ID=/subscriptions/.../resourceGroups/.../providers/Microsoft.MachineLearningServices/workspaces/.../projects/...
```

### 4. Create Data and Knowledge Bases

```bash
# Create search indexes
python data/01-create-index.py
python data/03-create-feedback-index.py

# Generate synthetic data (100k resumes + feedback)
python data/02-push-data.py --count 100000
python data/04-push-feedback-data.py

# Create Foundry IQ Knowledge Bases
pip install azure-search-documents==11.7.0b2
python data/09-create-knowledge-bases.py

# Create MCP connections in Foundry project
python data/10-create-mcp-connections.py
```

### 5. Test the Integration

```bash
# Run Foundry IQ integration tests
pytest tests/test_foundry_iq.py -v

# Or quick direct test
python tests/test_foundry_iq.py
```

### 6. Run the Web App

```bash
python main.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Workflow Example

```
1. User: "Hi"
   → Orchestrator handles directly (greeting)

2. User: "I need a Senior AI Engineer in Dubai"
   → Orchestrator → RoleCrafter (builds profile)

3. User: "Required: Python, LLMs, Azure. 5+ years."
   → Orchestrator → RoleCrafter (captures requirements)

4. User: "Search for candidates"
   → Orchestrator → TalentScout (searches resumes via Foundry IQ)

5. User: "Check feedback for candidate 1"
   → Orchestrator → InsightPulse (retrieves interview history)

6. User: "Send email to candidate 1"
   → Orchestrator → ConnectPilot (drafts outreach)

7. User: "What's the weather?"
   → Orchestrator handles directly (rejects off-topic)
```

---

## Project Structure

```
talent-reconnect-agent/
├── main.py                 # FastAPI server entry point
├── config.py               # Environment configuration
├── agents/                 # Agent definitions
│   ├── factory.py          # Creates and manages all agents
│   ├── orchestrator.py     # Routes messages to specialists
│   ├── role_crafter.py     # Builds candidate profiles
│   ├── talent_scout.py     # Searches resumes (Foundry IQ)
│   ├── insight_pulse.py    # Reviews feedback (Foundry IQ)
│   ├── connect_pilot.py    # Drafts outreach emails
│   └── market_radar.py     # Web research
├── api/
│   └── routes.py           # SSE streaming chat endpoints
├── data/                   # Index and KB setup scripts
├── tests/                  # Integration tests
└── static/
    └── index.html          # Chat UI
```

## License

MIT
