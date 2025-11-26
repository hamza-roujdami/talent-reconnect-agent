# Talent Reconnect Agent

> **⚠️ Demo Purpose Only**  
> This is a **proof-of-concept demonstration** showcasing AI-powered talent acquisition with Microsoft Agent Framework and Microsoft Foundry. It is **not production-ready code** and uses mock data for testing purposes. 

AI-powered multi-agent system for **Talent Acquisition** that reconnects qualified internal candidates with new opportunities using **Microsoft Agent Framework** and **Microsoft Foundry**.

## Architecture
```
Job Request → Orchestrator Agent (LLM-powered sequential router)
                    ↓
            ┌───────┴───────┐
            │ Classifier LLM │ 
            └───────┬───────┘
                    ↓
        SEQUENTIAL WORKFLOW (6 steps):
                    ↓
        1. Skills Mapping Agent
           ├─ Tool: extract_skills_from_job()
           └─ LLM extracts 10 canonical skills
                    ↓
        2. Resume Sourcing Agent
           ├─ Tool: search_resumes()
           ├─ Azure AI Search (hybrid: keyword + vector)
           └─ Returns top 10 matching candidates
                    ↓
        3. Historical Feedback Agent
           ├─ Tool: filter_by_feedback()
           └─ Filters based on ATS/CRM history
                    ↓
        4. Profile Enrichment Agent
           ├─ Tool: enrich_profile()
           └─ Adds current employment data
                    ↓
        5. TA Approval Agent (HITL)
           ├─ Tool: simulate_ta_approval()
           └─ LLM simulates human review
                    ↓
        6. Outreach Agent
           ├─ Tool: generate_outreach_message()
           └─ LLM generates personalized messages
```
## Use Case

The Talent Reconnect Agent automates the talent sourcing workflow:

1. **Job Analysis**: Takes a job title + description
2. **Skills Mapping**: Maps the role to ~10 canonical skills
3. **Candidate Search**: Searches internal resumes using Azure AI Search over Blob-stored CVs
4. **Historical Filtering**: Applies historical feedback from ATS/CRM (previous rejections, preferences)
5. **Profile Enrichment**: Enriches candidates with current job/company via compliant profile enrichment API
6. **Human-in-the-Loop**: TA manager reviews and approves candidates
7. **Outreach**: Sends personalized messages to approved candidates and logs to ATS/CRM

## Technical Implementation

### Tech Stack
- **Framework**: Microsoft Agent Framework (ChatAgent + OpenAIChatClient)
- **LLM**: Microsoft Foundry Models (gpt-4o-mini-deployment) with DefaultAzureCredential
- **Search**: Azure AI Search with hybrid search (keyword + vector + semantic)
- **Embeddings**: Azure OpenAI text-embedding-ada-002 (1536 dimensions)
- **Vector Algorithm**: HNSW with cosine similarity
- **UI**: Gradio web interface
- **Language**: Python 3.10+ with asyncio

### Orchestration Patterns

#### Sequential Workflow 
The talent acquisition process follows a strict sequential flow:
```
Job Analysis → Skills Mapping → Resume Sourcing → Historical Feedback 
    → Profile Enrichment → TA Approval → Outreach
```

#### Hybrid Search Architecture
Resume Sourcing uses 3-layer search:
1. **Keyword Search**: Traditional full-text search on skills, title, summary
2. **Vector Search**: Semantic similarity using 1536-dim embeddings (HNSW algorithm)
3. **Semantic Ranking**: Azure's L2 semantic ranker for better relevance

Query flow:
```
Skills → Generate Query Embedding → Hybrid Search (keyword + vector) 
    → Apply Filters (location, experience) → Semantic Ranking → Top 10 Results
```
## Quick Start

### Prerequisites

**Required:**
- Python 3.10 or higher
- Azure CLI installed and authenticated (`az login`)
- Azure Foundry project with GPT-4o-mini deployment
- Azure AI Search instance with Standard tier (for hybrid search)

**For Demo:**
- Mock data is included for historical feedback and profile enrichment
- Sample resumes provided in `data/sample_resumes.json`

**For Production:**
- ATS/CRM API integration (currently mocked)
- Compliant profile enrichment API (currently mocked)
- Real HITL dashboard (currently LLM-simulated)

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt --pre
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

**Core Configuration (Required):**

```bash
# Azure Foundry Configuration (for LLM agents)
OPENAI_API_BASE=https://your-project.services.ai.azure.com/models
OPENAI_MODEL_NAME=gpt-4o-mini-deployment

# Azure AI Search (for resume database)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-search-admin-key
AZURE_SEARCH_INDEX=resumes
```

The `data/setup_search.py` script includes hardcoded embedding configuration. For production, configure these via environment variables.

### 3. Set Up Azure AI Search (One-time)

**Important:** Update `data/setup_search.py` with your Azure Search credentials before running.

```bash
# Create search index and upload sample resumes with embeddings
python data/setup_search.py
```

This script will:
- Create a search index with 1536-dimension vector field (HNSW algorithm)
- Generate embeddings for 8 sample resumes using Azure OpenAI
- Upload documents to Azure AI Search
- Configure hybrid search capabilities (keyword + vector + semantic ranking)

**Note:** The script currently contains hardcoded credentials for demo purposes. Replace with environment variables for production use.

### 4. Run the Application

```bash
# Start Gradio web interface
python app.py

# Or test the orchestrator directly
python agents/orchestrator_agent.py
```

Open http://localhost:7861 in your browser.

### 5. Try the Demo Workflow

Paste this into the UI:

```
I need to find candidates for a Senior Machine Learning Engineer role.

Job Requirements:
- 5+ years experience in Python and machine learning
- Hands-on experience with Azure ML and MLOps practices
- Strong leadership and team collaboration skills
- Proven track record building production ML systems
- Experience with cloud platforms (Azure preferred)

Company: TechCorp Solutions
Location: Remote or San Francisco Bay Area
```
Continue with "continue" or "next step" to progress through the 6-step workflow.

## Resources

**Microsoft Agent Framework:**
- [Official Documentation](https://learn.microsoft.com/agent-framework/overview/agent-framework-overview)
- [GitHub Repository](https://github.com/microsoft/agent-framework)
- [HITL Patterns & Examples](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/AzureFunctions/05_AgentOrchestration_HITL)

**Azure AI Services:**
- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [Hybrid Search Overview](https://learn.microsoft.com/azure/search/hybrid-search-overview)
- [Vector Search Guide](https://learn.microsoft.com/azure/search/vector-search-overview)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure Foundry (AI Studio)](https://learn.microsoft.com/azure/ai-studio/)

**Related Projects:**
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel) - Alternative agent orchestration framework
- [Prompt Flow](https://microsoft.github.io/promptflow/) - LLM application development toolkit