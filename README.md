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
              │ Azure AI    │ │ Azure AI    │ │  SendEmail  │ │ WebSearch   │
              │ Search      │ │ Search      │ │  Function   │ │ Preview     │
              │ (resumes)   │ │ (feedback)  │ │             │ │             │
              └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Agents

| Agent | Key | Purpose | Tools |
|-------|-----|---------|-------|
| **Orchestrator** | `orchestrator` | Routes requests, handles greetings, rejects off-topic | None |
| **RoleCrafter** | `role-crafter` | Builds job profiles and gathers requirements | None |
| **TalentScout** | `talent-scout` | Searches 100k+ resumes | AzureAISearchAgentTool |
| **InsightPulse** | `insight-pulse` | Reviews interview feedback history | AzureAISearchAgentTool |
| **ConnectPilot** | `connect-pilot` | Drafts and sends outreach emails | FunctionTool |
| **MarketRadar** | `market-radar` | Researches salaries, trends, companies | WebSearchPreviewTool |

## Tech Stack

| Feature | Technology |
|---------|------------|
| **Multi-Agent Orchestration** | Azure AI Foundry Agents (Responses API) |
| **Model** | `gpt-5-mini` via Foundry |
| **Candidate Search** | `AzureAISearchAgentTool` (semantic ranking) |
| **Feedback Lookup** | `AzureAISearchAgentTool` (semantic ranking) |
| **Web Research** | `WebSearchPreviewTool` (no Bing resource needed) |
| **Session Persistence** | Azure Cosmos DB (with in-memory fallback) |
| **API Server** | FastAPI with SSE streaming |

## Quick Start

### Prerequisites

- Python 3.11+
- Azure subscription with:
  - Azure AI Foundry project
  - Azure AI Search (Standard tier for semantic search)
  - Azure Cosmos DB (optional)

### Setup

```bash
# 1. Clone and setup
git clone https://github.com/your-org/talent-reconnect-agent.git
cd talent-reconnect-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Create search indexes
python data/01-create-index.py
python data/02-push-data.py --count 100000
python data/03-create-feedback-index.py
python data/04-push-feedback-data.py

# 4. Run
python main.py
# Open http://localhost:8000
```

### Environment Variables

```bash
# Required
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
AZURE_AI_SEARCH_CONNECTION_NAME=your-search-connection
FOUNDRY_MODEL_PRIMARY=gpt-5-mini

# Optional
SEARCH_RESUME_INDEX=resumes
SEARCH_FEEDBACK_INDEX=feedback
ENABLE_WEB_SEARCH=true
```

## Workflow Example

```
1. User: "Hi"
   → Orchestrator handles directly (greeting)

2. User: "I need a Senior AI Engineer in Dubai"
   → Orchestrator → RoleCrafter (builds profile)

3. User: "Required: Python, LLMs, Azure. 5+ years."
   → Orchestrator → RoleCrafter (captures requirements)

4. User: "Search for candidates"
   → Orchestrator → TalentScout (searches resumes)

5. User: "Check feedback for candidate 1"
   → Orchestrator → InsightPulse (retrieves interview history)

6. User: "Send email to candidate 1"
   → Orchestrator → ConnectPilot (drafts outreach)

7. User: "What's the weather?"
   → Orchestrator handles directly (rejects off-topic)
```

## Testing

```bash
python tests/test_full_workflow.py
```

## License

MIT
