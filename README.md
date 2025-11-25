# Talent Reconnect Agent

> **⚠️ Demo Purpose Only**  
> This is a **proof-of-concept demonstration** showcasing AI-powered talent acquisition with Microsoft Agent Framework and Microsoft Foundry. It is **not production-ready code** and uses mock data for testing purposes. For production deployment, replace mock implementations with real integrations, add proper error handling, security measures, compliance checks, and scalability considerations.

AI-powered multi-agent system for **Talent Acquisition** that reconnects qualified internal candidates with new opportunities using **Microsoft Agent Framework** and **Azure Foundry**.

## Use Case

The Talent Reconnect Agent automates the talent sourcing workflow:

1. **Job Analysis**: Takes a job title + description
2. **Skills Mapping**: Maps the role to ~10 canonical skills
3. **Candidate Search**: Searches internal resumes using Azure AI Search over Blob-stored CVs
4. **Historical Filtering**: Applies historical feedback from ATS/CRM (previous rejections, preferences)
5. **Profile Enrichment**: Enriches candidates with current job/company via compliant profile enrichment API
6. **Human-in-the-Loop**: TA manager reviews and approves candidates
7. **Outreach**: Sends personalized messages to approved candidates and logs to ATS/CRM

## Architecture

```
Job Request → Supervisor Agent (Orchestration)
                    ↓
        ┌───────────┴───────────────────────┐
        ↓                                   ↓
   Skills Mapping Agent              Candidate Search Agent
   (Job → Skills)                    (Azure AI Search)
                    ↓
            Enrichment Agent
            (Profile API + ATS/CRM feedback)
                    ↓
            Approval Agent
            (Human-in-the-Loop)
                    ↓
            Outreach Agent
            (Messaging + ATS/CRM logging)
```

**Agents (To Be Implemented):**
- **Supervisor**: Orchestrates the sequential workflow
- **Skills Mapping Agent**: Analyzes job description and extracts canonical skills
- **Candidate Search Agent**: Queries Azure AI Search for matching CVs
- **Enrichment Agent**: Adds current employment data and historical feedback
- **Approval Agent**: HITL workflow for TA manager review
- **Outreach Agent**: Sends messages and logs to ATS/CRM

## Orchestration Patterns

### Sequential Workflow (Primary Pattern)
The talent acquisition process follows a strict sequential flow:
```
Job Analysis → Skills Mapping → Search → Enrichment → Approval → Outreach
```

Each step must complete before the next begins, ensuring data quality and compliance.

### Human-in-the-Loop (HITL)
The approval step requires explicit human decision-making:
- TA manager reviews enriched candidate profiles
- Approves/rejects each candidate
- Provides feedback for future improvements
- System waits for approval before proceeding to outreach

## Setup

### Prerequisites
- Python 3.10+
- Azure CLI (`az login`)
- Azure Foundry with model deployment
- Azure AI Search instance (for CV search)
- Azure Blob Storage (for CV storage)
- ATS/CRM API credentials (for feedback and logging)
- Profile enrichment API credentials (compliant data source)

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt --pre

# Configure .env file (see .env.example)
cp .env.example .env
# Edit .env with your Azure services credentials
```

### Required Environment Variables

```bash
# Azure Foundry
AZURE_OPENAI_ENDPOINT=https://your-foundry-endpoint.services.ai.azure.com/models
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini-deployment

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_INDEX_NAME=resumes-index

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_STORAGE_CONTAINER_NAME=resumes

# ATS/CRM API (mock for demo)
ATS_API_ENDPOINT=https://your-ats-api.com
ATS_API_KEY=your-api-key

# Profile Enrichment API (mock for demo)
ENRICHMENT_API_ENDPOINT=https://your-enrichment-api.com
ENRICHMENT_API_KEY=your-api-key
```

## Features

### 🎯 Skills Mapping
- Canonical skills taxonomy (standardized skill names)
- LLM-powered extraction from job descriptions
- ~10 most relevant skills per role
- Handles ambiguous or non-standard job titles

### 🔍 Intelligent Search
- Azure AI Search with semantic ranking
- Vector embeddings for CV similarity
- Filters: location, availability, experience level
- Historical feedback weighting

### 📊 Profile Enrichment
- Current employment status (via compliant API)
- Company information and tenure
- Previous interaction history (ATS/CRM)
- Rejection reasons and feedback notes

### ✅ Human-in-the-Loop
- TA manager dashboard for candidate review
- Approve/reject with reasoning
- Batch approval support
- Audit trail of decisions

### 📧 Automated Outreach
- Personalized messaging templates
- Multi-channel support (email, LinkedIn, SMS)
- ATS/CRM integration for activity logging
- Compliance checks (GDPR, opt-out preferences)

## Development Roadmap

- [ ] Set up Azure AI Search index for resumes
- [ ] Implement Skills Mapping Agent
- [ ] Implement Candidate Search Agent with Azure AI Search
- [ ] Build Enrichment Agent with ATS/CRM integration
- [ ] Create HITL Approval Agent workflow
- [ ] Develop Outreach Agent with messaging and logging
- [ ] Build Supervisor Agent for orchestration
- [ ] Create Gradio web UI for TA managers
- [ ] Add observability and tracing
- [ ] Production deployment guide

## Compliance & Ethics

⚠️ **Important Considerations:**
- **GDPR Compliance**: Ensure consent for candidate data processing
- **Data Retention**: Follow organizational policies for CV storage
- **Bias Prevention**: Regular audits of AI recommendations
- **Opt-Out Respect**: Honor candidate communication preferences
- **Transparency**: Clear communication about AI usage in recruitment
- **Data Security**: Encrypt sensitive candidate information

## Resources

- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/agent-framework/overview/agent-framework-overview)
- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [Human-in-the-Loop Patterns](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/AzureFunctions/05_AgentOrchestration_HITL)

## .NET Implementation

For customers coding in .NET, see [dotnet.md](dotnet.md) for equivalent patterns and samples from the Microsoft Agent Framework.

## License

Demo project for educational purposes.
