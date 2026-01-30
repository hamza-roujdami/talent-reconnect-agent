# Talent Reconnect - Infrastructure

Production-grade Azure AI Foundry infrastructure with **enterprise networking** for the Talent Reconnect AI recruiting agent.

## 🏗️ Architecture

```
                                    Internet
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │   Application Gateway + WAF  │
                        │   (tragt-appgw-4pwr)         │
                        │   Public IP: 20.91.190.46    │
                        │   WAF v2: OWASP 3.2 + Bot    │
                        └──────────────┬───────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                    Virtual Network (192.168.0.0/16)                          │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │  appgw-subnet (192.168.5.0/24)    │                                   │  │
│  └───────────────────────────────────┼───────────────────────────────────┘  │
│                                      │                                       │
│                         ┌────────────┴────────────┐                         │
│                         ▼                         ▼                         │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐        │
│  │   API Management (BasicV2)   │  │    Container Apps Env        │        │
│  │   tragt-apim-4pwr            │  │    tragt-ca-env-4pwr         │        │
│  │   AI Gateway Policies        │◄─┤    (Talent Reconnect App)    │        │
│  │   apim-subnet (192.168.4.0/27)  │    app-subnet (192.168.2.0/23)│        │
│  └──────────────────────────────┘  └──────────────────────────────┘        │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │      Agent Subnet (192.168.0.0/24) - EXCLUSIVE for AI Foundry         │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │   Capability Host (caphostproj) - Agent Runtime                │   │  │
│  │  │   Delegated to: Microsoft.App/environments                     │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │      Private Endpoint Subnet (192.168.1.0/24)                         │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │  │
│  │  │AI Foundry│ │ Cosmos DB│ │AI Search │ │ Storage  │                  │  │
│  │  │  (PE)    │ │   (PE)   │ │   (PE)   │ │   (PE)   │                  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          ▼                            ▼                            ▼
   ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
   │  Cosmos DB  │            │  AI Search  │            │   Storage   │
   │  (Threads)  │            │(100K Resumes│            │   (Files)   │
   │  Serverless │            │ + Feedback) │            │ Standard_ZRS│
   └─────────────┘            └─────────────┘            └─────────────┘
```

## 📦 Resources Deployed

### Core AI Infrastructure

| Resource | Purpose | Name | SKU |
|----------|---------|------|-----|
| **AI Foundry Account** | AI services hub with model deployments | `tragt4pwr` | S0 |
| **AI Foundry Project** | Workspace for agents | `trproj4pwr` | - |
| **Capability Host** | Agent runtime (Standard Setup) | `caphostproj` | Agents |
| **Azure Cosmos DB** | Thread/conversation persistence | `tragt4pwrcosmosdb` | Serverless |
| **Azure AI Search** | Vector store (100K resumes + feedback) | `tragt4pwrsearch` | Standard |
| **Azure Storage** | File storage for agent artifacts | `tragt4pwrstorage` | Standard_ZRS |

### Application Hosting

| Resource | Purpose | Name | SKU |
|----------|---------|------|-----|
| **API Management** | AI Gateway with policies | `tragt-apim-4pwr` | BasicV2 |
| **Container Apps Env** | Application hosting | `tragt-ca-env-4pwr` | Consumption |
| **Container Registry** | Docker image storage | `tragtcaacr4pwr` | Basic |
| **Application Insights** | Tracing & telemetry | `tragt-appi` | - |
| **Log Analytics** | Centralized logging | `tragt-law` | PerGB2018 |

### Networking & Security

| Resource | Purpose | Name |
|----------|---------|------|
| **Virtual Network** | Network isolation | `talentreconnect-vnet` (192.168.0.0/16) |
| **Application Gateway** | Public ingress + WAF | `tragt-appgw-4pwr` |
| **WAF Policy** | OWASP 3.2 + Bot protection | `tragt-appgw-4pwr-waf-policy` |
| **Private Endpoints** | Secure connectivity | 4 endpoints (AI, Cosmos, Search, Storage) |
| **Private DNS Zones** | Name resolution | 7 zones |
| **NSGs** | Network security | 2 (App Gateway, APIM) |

### Subnet Layout

| Subnet | CIDR | Purpose | Delegation |
|--------|------|---------|------------|
| `agent-subnet` | 192.168.0.0/24 | AI Foundry Agents (EXCLUSIVE) | Microsoft.App/environments |
| `pe-subnet` | 192.168.1.0/24 | Private Endpoints | - |
| `app-subnet` | 192.168.2.0/23 | Container Apps | Microsoft.App/environments |
| `apim-subnet` | 192.168.4.0/27 | API Management | Microsoft.Web/serverFarms |
| `appgw-subnet` | 192.168.5.0/24 | Application Gateway | - |

## 🚀 Deployment

### Prerequisites

1. **Azure CLI** with Bicep extension
2. **Azure subscription** with the following permissions:
   - Owner or Contributor on the subscription
   - Ability to create service principals
3. **Registered providers**:
   ```bash
   az provider register --namespace Microsoft.CognitiveServices
   az provider register --namespace Microsoft.DocumentDB
   az provider register --namespace Microsoft.Search
   az provider register --namespace Microsoft.Storage
   az provider register --namespace Microsoft.Network
   az provider register --namespace Microsoft.App
   ```

### Deploy

```bash
# 1. Create resource group
az group create \
  --name rg-talentreconnect-prod \
  --location swedencentral \
  --tags project=talent-reconnect-agent environment=prod

# 2. Deploy infrastructure (15-25 minutes)
az deployment group create \
  --resource-group rg-talentreconnect-prod \
  --template-file main.bicep \
  --parameters main.bicepparam \
  --name talentreconnect-$(date +%Y%m%d)
```

### Verify Deployment

```bash
# Check deployment status
az deployment group show \
  --resource-group rg-talentreconnect-prod \
  --name <deployment-name> \
  --query "properties.provisioningState"

# List resources
az cognitiveservices account list -g rg-talentreconnect-prod -o table
az search service list -g rg-talentreconnect-prod -o table
az cosmosdb list -g rg-talentreconnect-prod -o table
az storage account list -g rg-talentreconnect-prod -o table
```

## ⚙️ Configuration

### Parameters (`main.bicepparam`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `location` | Azure region | `swedencentral` |
| `aiServices` | Base name for AI services | `tragt` |
| `firstProjectName` | Project name prefix | `trproj` |
| `modelName` | Model to deploy | `gpt-4o-mini` |
| `modelCapacity` | TPM capacity | `30` |
| `vnetName` | Virtual network name | `talentreconnect-vnet` |

### Supported Regions

Class A subnet support (GA):
- Australia East, Brazil South, Canada East
- **East US, East US 2**, France Central
- Germany West Central, Italy North, Japan East
- South Africa North, South Central US, South India
- Spain Central, **Sweden Central**, UAE North
- UK South, West Europe, **West US, West US 3**

## 🔐 Security Features

| Feature | Description |
|---------|-------------|
| **Application Gateway WAF** | OWASP 3.2 + Bot Manager in Prevention mode |
| **Private Endpoints** | AI Foundry, Cosmos, Search, Storage on private IPs |
| **Network Isolation** | VNet with 5 subnets for proper segmentation |
| **NSG Rules** | Ingress/egress controls on App Gateway & APIM subnets |
| **No Public Access** | Backend resources accessible only via private endpoints |
| **Managed Identity** | System-assigned identity for RBAC |
| **Local Auth Disabled** | Cosmos DB uses AAD only |
| **TLS 1.2** | Minimum TLS version enforced |

### Traffic Flow

```
Internet
    │
    ▼
Application Gateway (WAF v2 - Prevention Mode)
    │  Public IP: 20.91.190.46
    │  FQDN: tragt-appgw-4pwr.swedencentral.cloudapp.azure.com
    │
    ├──► API Management ──► Container Apps ──► AI Foundry (via PE)
    │    (AI Gateway)       (App Runtime)      (Agent Runtime)
    │
    └──► Direct to Container Apps (optional)
```

## 🗂️ File Structure

```
infra/
├── README.md                         # This file
├── main.bicep                        # Core AI infrastructure (AI Foundry, Cosmos, Search, Storage)
├── main.bicepparam                   # Core infrastructure parameters
├── app-hosting.bicep                 # App hosting (APIM, Container Apps, App Insights)
├── app-hosting.bicepparam            # App hosting parameters
├── network-security.bicep            # Network security (App Gateway, WAF, NSGs)
├── network-security.bicepparam       # Network security parameters
├── deleteCapHost.sh                  # Cleanup script for capability host
└── modules-network-secured/          # Bicep modules
    ├── ai-account-identity.bicep
    ├── ai-project-identity.bicep
    ├── ai-search-role-assignments.bicep
    ├── add-project-capability-host.bicep
    ├── api-management.bicep              # APIM with AI Gateway policies
    ├── application-gateway.bicep         # App Gateway with WAF v2
    ├── application-insights.bicep        # App Insights + Log Analytics
    ├── azure-storage-account-role-assignment.bicep
    ├── blob-storage-container-role-assignments.bicep
    ├── container-apps-environment.bicep  # Container Apps Environment
    ├── cosmos-container-role-assignments.bicep
    ├── cosmosdb-account-role-assignment.bicep
    ├── existing-vnet.bicep
    ├── format-project-workspace-id.bicep
    ├── network-agent-vnet.bicep
    ├── private-endpoint-and-dns.bicep
    ├── standard-dependent-resources.bicep
    ├── subnet.bicep
    ├── validate-existing-resources.bicep
    └── vnet.bicep
```

## 🧹 Cleanup

### Delete Capability Host First

Before deleting the resource group, delete the capability host to avoid orphaned resources:

```bash
# Run the cleanup script
chmod +x deleteCapHost.sh
./deleteCapHost.sh
```

### Delete Resource Group

```bash
az group delete --name rg-talentreconnect-sweden --yes --no-wait
```

## 📝 Notes

### APIM VNet Integration

The current APIM is **BasicV2** which does not support VNet integration. Traffic flows:
- **Public path**: Internet → App Gateway (WAF) → APIM → Container Apps
- **APIM Gateway URL**: `https://tragt-apim-4pwr.azure-api.net`

To enable VNet integration, upgrade to **Standard v2** (~$1,500/mo) or **Premium v2** (~$3,000/mo).

### AI Foundry Agent Subnet

The `agent-subnet` is **EXCLUSIVE** to AI Foundry. Per Microsoft documentation:
> "You must ensure the subnet is not already in use by another account. It must be an exclusive subnet for the Foundry account."

Do not deploy any other resources to this subnet.

## 📊 Current Deployment

**Resource Group:** `rg-talentreconnect-sweden`  
**Location:** Sweden Central  
**Deployed:** January 30, 2026

### Core AI Resources

| Resource | Name | Endpoint |
|----------|------|----------|
| AI Foundry Account | `tragt4pwr` | `https://tragt4pwr.cognitiveservices.azure.com/` |
| AI Foundry Project | `trproj4pwr` | - |
| Capability Host | `caphostproj` | - |
| Cosmos DB | `tragt4pwrcosmosdb` | `https://tragt4pwrcosmosdb.documents.azure.com:443/` |
| AI Search | `tragt4pwrsearch` | Private only (via VNet) |
| Storage | `tragt4pwrstorage` | Private only (via VNet) |

### Application & Networking Resources

| Resource | Name | Endpoint |
|----------|------|----------|
| Application Gateway | `tragt-appgw-4pwr` | `tragt-appgw-4pwr.swedencentral.cloudapp.azure.com` |
| Public IP | `tragt-appgw-4pwr-pip` | `20.91.190.46` |
| API Management | `tragt-apim-4pwr` | `https://tragt-apim-4pwr.azure-api.net` |
| Container Apps Env | `tragt-ca-env-4pwr` | - |
| Container Registry | `tragtcaacr4pwr` | `tragtcaacr4pwr.azurecr.io` |
| Application Insights | `tragt-appi` | - |
| Log Analytics | `tragt-law` | - |
| VNet | `talentreconnect-vnet` | 192.168.0.0/16 |

### Deployment Commands

```bash
# 1. Deploy core AI infrastructure (AI Foundry, Cosmos, Search, Storage)
az deployment group create \
  --resource-group rg-talentreconnect-sweden \
  --template-file main.bicep \
  --parameters main.bicepparam

# 2. Deploy app hosting (APIM, Container Apps, App Insights)
az deployment group create \
  --resource-group rg-talentreconnect-sweden \
  --template-file app-hosting.bicep \
  --parameters app-hosting.bicepparam

# 3. Deploy network security (App Gateway, WAF, NSGs)
az deployment group create \
  --resource-group rg-talentreconnect-sweden \
  --template-file network-security.bicep \
  --parameters network-security.bicepparam
```

## 🔗 Related Documentation

- [Azure AI Foundry Agent Service](https://learn.microsoft.com/azure/ai-foundry/agents/)
- [Standard Agent Setup](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/standard-agent-setup)
- [Network Isolation](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/virtual-network)
- [Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
