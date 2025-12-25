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
- **Tests/Demos** run straight against the workflow: [tests/demo_test.py](tests/demo_test.py) replays the six-step scenario, while [tests/test_workflow.py](tests/test_workflow.py) exposes a CLI REPL for observing agent/tool hops.


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

# Optional CLI demo/test harnesses
python tests/demo_test.py   # Scripted six-step hiring demo
python tests/test_workflow.py   # Interactive workflow debugger
```

---

## Project Structure

```
talent-reconnect-agent/
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
├── tests/                  # Demo + debugging harnesses
│   ├── demo_test.py        # scripted end-to-end demo
│   ├── test_workflow.py    # interactive multi-agent REPL
│   └── debug_tools.py      # utility to inspect registered tools
├── tools/
│   ├── search_provider.py  # Azure AI Search provider helpers
│   ├── feedback_lookup.py  # Feedback lookup
│   └── outreach_email.py   # Outreach drafts
```

---

## License

MIT
