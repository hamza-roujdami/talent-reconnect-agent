# Talent Reconnect Agent

AI-powered Talent Acquisition Agent using **Microsoft Agent Framework (MAF)** and **Azure AI Search**

> ⚠️ **Demo purposes only** - Not intended for production use.

---

## Demo Flow


`User needs ML engineer → Orchestrator routes to ProfileAgent for JD → SearchAgent queries Azure AI Search → InsightsAgent reviews interview history → OutreachAgent drafts the email.`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator                               │
│            (Routes requests to specialists)                     │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌──────────────┐┌─────────────┐
│  Profile    │ │   Search    │ │   Insights   ││  Outreach   │
│   Agent     │ │   Agent     │ │    Agent     ││   Agent     │
└─────────────┘ └─────────────┘ └──────────────┘└─────────────┘
                      │              │
                      ▼              ▼
              ┌─────────────┐ ┌─────────────┐
              │ Azure AI    │ │ Azure AI    │
              │ Search      │ │ Search      │
              │ (resumes)   │ │ (feedback)  │
              └─────────────┘ └─────────────┘
```

**Under the hood**
- **Agents** are instantiated via Microsoft Agent Framework’s `HandoffBuilder` on top of Foundry’s GPT‑4o mini deployment. Each specialist carries purpose-built instructions plus zero- or low-temperature sampling so they stay deterministic during the demo.
- **Search context** comes from custom helper modules in [tools/search_provider.py](tools/search_provider.py#L1-L116) and [tools/feedback_lookup.py](tools/feedback_lookup.py#L1-L252). They wrap `AzureAISearchContextProvider` (semantic or agentic modes) and hydrate the Resume + Feedback indexes with the data scripts in [data/](data/README.md).
- **Tools** (e.g., `send_outreach_email`, `lookup_feedback_by_ids`) live in [tools/outreach_email.py](tools/outreach_email.py) and the insights helpers. They’re regular Python callables exposed to the Agent Framework so LLM responses can invoke them deterministically.
- **API + UI** are served via FastAPI (`main.py` + [api/routes.py](api/routes.py)) with Server-Sent Events streaming into [static/index.html](static/index.html). Pending-request TTLs and the scripted demo panel keep the workflow predictable for exec demos.
- **Tests/Demos** run straight against the workflow: [tests/test_demo.py](tests/test_demo.py) replays the five-step scenario, while [tests/test_agents.py](tests/test_agents.py) covers unit tests for agent wiring.
- **Checkpointing** is enabled via MAF's `FileCheckpointStorage`. Workflow state persists to `.checkpoints/` so conversations can survive server restarts (see `api/routes.py`).
- **Observability** sends traces and dependencies to Azure Application Insights via OpenTelemetry (see `observability.py`).

---

## Observability

Telemetry is sent to Azure Application Insights when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set in `.env`.

**What's captured:**
- **Traces** – Agent activity, handoffs, tool calls
- **Dependencies** – Azure AI Search queries, LLM requests

**View in Azure Portal:**
1. Go to your Application Insights resource
2. **Transaction search** → Filter by `traces` or `dependencies`
3. **Application map** → See service dependencies visually

**Disable:** Remove `APPLICATIONINSIGHTS_CONNECTION_STRING` from `.env` or leave it empty.

---

## Environment Variables

> Copy `.env.example` to `.env` and replace each placeholder before running any scripts.

- `AZURE_SEARCH_MODE=agentic` and `AZURE_FEEDBACK_MODE=agentic` (default in `.env.example`) force both resume and feedback retrieval paths into knowledge-base/agentic mode. Switch them back to `semantic` if you prefer vector search with semantic configs.

---

## Data Setup

Scripts for Azure AI Search live under `data/`.

```bash
# 1. Create indexes
python data/01-create-index.py           # resumes index
python data/03-create-feedback-index.py  # optional feedback index

# 2. Upload data
python data/02-push-data.py --count 100000                           # synthetic resumes
python data/04-push-feedback-data.py --total-feedback 60000          # optional interview feedback corpus

# 3. Verify
python data/05-resumes-semantic-harness.py "Find Senior Python developers in Dubai"
python data/07-feedback-semantic-harness.py "Which candidates carry no-hire red flags?"
```

---

## Quick Start

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials

# Run
python chat_multi.py        # Multi-agent terminal chat
python main.py              # FastAPI server + browser UI on :8000

# Tests
python tests/test_demo.py              # Scripted 5-step hiring demo
pytest tests/test_agents.py -v         # Agent unit tests
pytest tests/test_search.py -v         # Search integration tests (requires Azure)
```

---

## Project Structure

```
talent-reconnect-agent/
├── .checkpoints/           # Workflow state persistence (ignored in git)
├── chat_multi.py           # Multi-agent terminal chat
├── main.py                 # FastAPI server
├── agents/
│   ├── factory.py          # create_recruiting_workflow()
│   ├── profile_agent.py
│   ├── search_agent.py
│   ├── insights_agent.py
│   └── outreach_agent.py
├── data/                   # Azure AI Search setup scripts & harnesses
│   ├── 05-resumes-semantic-harness.py   # resumes semantic validation
│   ├── 06-resumes-agentic-harness.py    # resumes agentic validation
│   ├── 07-feedback-semantic-harness.py  # feedback semantic validation
│   └── 08-feedback-agentic-harness.py   # feedback agentic validation
├── tests/                  # Test suite
│   ├── conftest.py         # pytest fixtures
│   ├── test_demo.py        # scripted 5-step hiring demo
│   ├── test_agents.py      # agent unit tests
│   ├── test_search.py      # search integration tests
│   ├── test_api.py         # API endpoint tests
│   └── utils/              # test utilities
├── tools/
│   ├── search_provider.py  # Azure AI Search provider helpers
│   ├── feedback_lookup.py  # Feedback lookup
│   └── outreach_email.py   # Outreach drafts
```

---

## License

MIT
