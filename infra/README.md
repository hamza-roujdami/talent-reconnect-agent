# Infrastructure as Code

Bicep templates to deploy all Azure resources for the Talent Reconnect Agent.

## Resources Deployed

| Resource | Description |
|----------|-------------|
| **Resource Group** | `rg-talentreconnect-{env}` |
| **AI Foundry Account** | Azure AI Services with project management |
| **AI Project** | Workspace for the recruiting agents |
| **GPT-4o-mini** | Primary LLM (fast, cost-effective) |
| **GPT-4o** | Secondary LLM (more capable) |
| **text-embedding-3-large** | Embedding model for semantic search |
| **Azure AI Search** | Knowledge base for resumes and feedback |
| **Log Analytics** | Workspace for logs and metrics |
| **Application Insights** | APM and tracing |

## Prerequisites

1. **Azure CLI** with Bicep extension:
   ```bash
   az bicep install
   az bicep upgrade
   ```

2. **Azure subscription** with permissions to create resources

3. **Sign in to Azure**:
   ```bash
   az login
   az account set --subscription "<your-subscription-id>"
   ```

## Deploy

### Option 1: Quick Deploy (defaults)

```bash
cd infra

# Deploy with default parameters
az deployment sub create \
  --location eastus2 \
  --template-file main.bicep \
  --parameters main.bicepparam
```

### Option 2: Custom Parameters

```bash
az deployment sub create \
  --location eastus2 \
  --template-file main.bicep \
  --parameters baseName=mytalentapp \
  --parameters environment=prod \
  --parameters searchSku=standard
```

### Option 3: What-If (Preview Changes)

```bash
az deployment sub what-if \
  --location eastus2 \
  --template-file main.bicep \
  --parameters main.bicepparam
```

## Post-Deployment Steps

### 1. Get Search API Key

```bash
# Get the resource group and search service names from outputs
RG_NAME=$(az deployment sub show --name main --query properties.outputs.resourceGroupName.value -o tsv)
SEARCH_NAME=$(az deployment sub show --name main --query properties.outputs.searchName.value -o tsv)

# Get the admin key
az search admin-key show \
  --resource-group $RG_NAME \
  --service-name $SEARCH_NAME \
  --query primaryKey -o tsv
```

### 2. Create `.env` File

Copy the output values to your `.env` file:

```bash
# Get deployment outputs
az deployment sub show --name main --query properties.outputs -o json
```

Then update your `.env`:

```env
# Microsoft Foundry (Azure AI)
FOUNDRY_CHAT_ENDPOINT=https://ai-talentreconnect-xxx.openai.azure.com/
FOUNDRY_MODEL_PRIMARY=gpt-4o-mini
FOUNDRY_MODEL_FAST=gpt-4o

# Azure AI Search
SEARCH_SERVICE_ENDPOINT=https://search-talentreconnect-xxx.search.windows.net
SEARCH_SERVICE_API_KEY=<your-admin-key>
SEARCH_RESUME_INDEX=resumes
SEARCH_FEEDBACK_INDEX=feedback
AZURE_SEARCH_MODE=agentic
AZURE_FEEDBACK_MODE=agentic

# Application Insights (optional)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;...
```

### 3. Bootstrap Search Indexes

After deployment, create the search indexes and upload data:

```bash
cd ..
python data/01-create-index.py
python data/03-create-feedback-index.py
python data/02-push-data.py --count 100000
python data/04-push-feedback-data.py --total-feedback 60000
```

### 4. Run the Demo

```bash
python main.py  # Web UI at http://localhost:8000
```

## Clean Up

Delete all resources:

```bash
az group delete --name rg-talentreconnect-dev --yes --no-wait
```

## Cost Estimate (Monthly)

| Resource | SKU | Estimated Cost |
|----------|-----|----------------|
| AI Foundry | S0 | Pay-per-token (~$5-50 for demos) |
| GPT-4o-mini | GlobalStandard | ~$0.15/1M input tokens |
| GPT-4o | GlobalStandard | ~$2.50/1M input tokens |
| Azure AI Search | Standard | ~$250/month |
| Application Insights | Pay-as-you-go | ~$2.30/GB ingested |
| Log Analytics | PerGB2018 | ~$2.30/GB |

**Demo usage**: ~$260-300/month (mostly Search)  
**Tip**: Use `basic` SKU for Search (~$75/mo) during development.

## Troubleshooting

### Deployment Fails with Quota Error

Some regions have limited model capacity. Try:
- `eastus2`, `westus2`, or `swedencentral`
- Request quota increase in Azure Portal

### Model Deployment Conflicts

Models are deployed serially to avoid conflicts. If you see errors, wait and retry:

```bash
az deployment sub create --location eastus2 --template-file main.bicep --parameters main.bicepparam
```

### Search Service Not Available

The Search SKU might not be available in your region. Check:
```bash
az search list-supported-tiers --location eastus2
```
