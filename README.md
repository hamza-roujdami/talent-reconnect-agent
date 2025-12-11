# Talent Reconnect Agent

AI-powered talent acquisition workflow using **Microsoft Agent Framework (MAF)**.

## Flow

1. **User:** "AI Engineer"
2. **Agent:** Generates job description → asks "proceed?"
3. **User:** "proceed"
4. **Agent:** Shows candidate comparison table → asks "send emails?"
5. **User:** "send emails to top 3"
6. **Agent:** Sends personalized outreach

## Structure

```
├── app.py              # CLI entry point
├── workflow.py         # MAF WorkflowBuilder + HITL
├── agents/             # ChatAgent definitions
├── tools/              # search, email functions
└── data/               # Mock resume data
```

## Run

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your COMPASS_API_KEY, COMPASS_BASE_URL, COMPASS_MODEL

# Run
python app.py
```

## MAF Features Used

- `WorkflowBuilder` - Workflow orchestration
- `Executor` + `@handler` - Custom workflow logic
- `ctx.request_info()` - Human-in-the-loop pauses
- `@response_handler` - Resume on user input
- `ChatAgent` - LLM-powered agents with tools
