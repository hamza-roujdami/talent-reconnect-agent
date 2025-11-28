# 🎯 Talent Reconnect Agent

**Human-in-the-Loop AI workflow** for talent acquisition using Microsoft Agent Framework.

> **Demo Project** - Showcases interactive multi-agent orchestration with HITL approval patterns. Not production-ready.

## ✨ What It Does

Automates talent sourcing with **HR approval at every step**:

1. **Skills Mapping** → Extract key skills from job description
2. **Resume Search** → Find candidates via Azure AI Search (hybrid keyword + vector)
3. **History Filter** → Remove recently contacted candidates
4. **Profile Enrichment** → Add current employment data
5. **TA Review** → Present candidates for approval
6. **Outreach** → Generate personalized messages

**Each step pauses for human approval before continuing.**

## 🏗️ Architecture

```
                 TurnManager Executor
                         ↓
    ┌────────────────────┴────────────────────┐
    │                                         │
Agent 1 → [PAUSE] → HR Approval → Agent 2 → [PAUSE] → HR Approval → ...
    │                                         │
    └──────── ctx.request_info() ────────────┘
```

**Key Components:**
- **Supervisor Agent:** MAF WorkflowBuilder with TurnManager Executor
- **6 MAF Agents:** ChatAgent with Azure OpenAI (GPT-4o-mini)
- **HITL Pattern:** `ctx.request_info()` pauses, `@response_handler` resumes
- **Azure AI Search:** Hybrid keyword + vector search (HNSW)
- **MCP Servers:** ATS/CRM history lookup, profile enrichment tools
- **Auth:** DefaultAzureCredential for all Azure services

## 🔧 How It Works

**Supervisor Built with MAF WorkflowBuilder:**

```python
# Create 6 ChatAgents
agents = [
    ("Skills Mapping", create_skill_mapping_agent(chat_client)),
    ("Resume Sourcing", create_resume_sourcing_agent(chat_client)),
    ("Historical Feedback", create_historical_feedback_agent(chat_client)),
    ("Profile Enrichment", create_profile_enricher_agent(chat_client)),
    ("TA Approval", create_ta_approval_agent(chat_client)),
    ("Outreach", create_outreach_agent(chat_client))
]

# TurnManager orchestrates all 6 agents with HITL
turn_manager = TurnManager(agents=agents)
workflow = WorkflowBuilder().set_start_executor(turn_manager).build()
```

**HITL Pattern:**

```python
class TurnManager(Executor):
    @handler
    async def start(self, job_request: str, ctx: WorkflowContext):
        result = await self.agents[0].run(job_request)  # Run first agent
        await ctx.request_info(approval_request, response_type=str)  # Pause
    
    @response_handler
    async def on_approval(self, original_request, user_input, ctx):
        self.current_step += 1
        if self.current_step < len(self.agents):
            result = await self.agents[self.current_step].run(prev_result.text)
            await ctx.request_info(...)  # Pause again
        else:
            await ctx.yield_output(final_result)  # Complete
```

**Flow:** `workflow.run()` → agent 1 → `ctx.request_info()` → **[PAUSE]** → `send_responses()` → `@response_handler` → agent 2 → repeat
## 🚀 Quick Start

### 1. Setup

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --pre

# Configure environment
cp .env.example .env
# Edit .env with your Azure credentials
```

### 2. Configure `.env`

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-key
AZURE_SEARCH_INDEX=resumes
```

**Authentication:** Login with `az login` for DefaultAzureCredential.

### 3. Setup Azure AI Search (one-time)

```bash
python data/setup_search.py  # Creates index + uploads sample resumes
```

### 4. Run

```bash
python talent-reconnect-agent.py
```

## 💡 Example Prompt

When prompted for a job description, use a detailed request like this:

```
We are looking for a Senior Machine Learning Engineer to join TechCorp Solutions.

Requirements:
- 5+ years of experience in Python and machine learning
- Hands-on experience with Azure ML, MLOps, and cloud platforms
- Strong leadership and team collaboration skills
- Experience building production ML systems
- Background in data engineering is a plus

Location: Remote or San Francisco Bay Area
Team: AI Platform Team
```

**What happens:**
1. **Skills Mapping** extracts: Python, Machine Learning, Azure ML, MLOps, Leadership, etc.
2. **Resume Sourcing** searches Azure AI Search for matching candidates
3. **Historical Feedback** filters out recently contacted candidates
4. **Profile Enrichment** adds current job/company info
5. **TA Approval** presents shortlist for review
6. **Outreach** generates personalized recruitment messages

**Approval Flow:**
- After each step, type `continue` to proceed
- Or type feedback/adjustments if needed
- At final step, type `email` or `message` to confirm outreach method

## 📁 Project Structure

```
talent-reconnect-agent/
├── talent-reconnect-agent.py       # Main interactive workflow
├── agents/
│   ├── supervisor.py               # TurnManager orchestrator
│   ├── skill_mapping_agent.py      # Extract skills
│   ├── resume_sourcing_agent.py    # Search candidates
│   ├── historical_feedback_agent.py # Filter by history
│   ├── profile_enricher_agent.py   # Enrich profiles
│   ├── ta_approval_hitl_agent.py   # Review candidates
│   └── outreach_agent.py           # Generate messages
└── data/
    ├── sample_resumes.json         # Mock data
    └── setup_search.py             # Index setup
```

## 📚 Resources

**Microsoft Agent Framework:** [Docs](https://learn.microsoft.com/agent-framework) | [HITL Examples](https://github.com/microsoft/agent-framework/tree/main/python/samples/learn/workflows/human-in-the-loop)

**Azure:** [AI Search](https://learn.microsoft.com/azure/search/) | [OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)

---

*Demo project for educational purposes only.*

