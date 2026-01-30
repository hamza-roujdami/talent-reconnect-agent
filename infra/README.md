# Talent Reconnect - Infrastructure

Production-grade Azure AI Foundry infrastructure with **full network isolation** for the Talent Reconnect AI recruiting agent.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Virtual Network (192.168.0.0/16)                  │
├─────────────────────────────┬───────────────────────────────────────┤
│      Agent Subnet           │      Private Endpoint Subnet          │
│    (192.168.0.0/24)         │        (192.168.1.0/24)               │
│                             │                                       │
│  ┌───────────────────────┐  │  ┌─────────────────────────────────┐ │
│  │   Capability Host     │  │  │   Private Endpoints:            │ │
│  │   (Agent Runtime)     │◄─┼──┤   • AI Foundry                  │ │
│  │                       │  │  │   • OpenAI / Cognitive Services │ │
│  │   Delegated to:       │  │  │   • Azure AI Search             │ │
│  │   Microsoft.App/      │  │  │   • Cosmos DB                   │ │
│  │   environments        │  │  │   • Blob Storage                │ │
│  └───────────────────────┘  │  └─────────────────────────────────┘ │
└─────────────────────────────┴───────────────────────────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
   ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
   │  Cosmos DB  │              │  AI Search  │              │   Storage   │
   │  (Threads)  │              │  (Vectors)  │              │   (Files)   │
   └─────────────┘              └─────────────┘              └─────────────┘
```

## 📦 Resources Deployed

| Resource | Purpose | SKU |
|----------|---------|-----|
| **AI Foundry Account** | AI services hub with model deployments | S0 |
| **AI Foundry Project** | Workspace for agents | - |
| **Capability Host** | Agent runtime (Standard Setup) | Agents |
| **Azure Cosmos DB** | Thread/conversation persistence | Serverless |
| **Azure AI Search** | Vector store for knowledge retrieval | Standard |
| **Azure Storage** | File storage for agent artifacts | Standard_ZRS |
| **Virtual Network** | Network isolation | /16 |
| **Private Endpoints** | Secure connectivity (4 endpoints) | - |
| **Private DNS Zones** | Name resolution (7 zones) | - |

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
| **Private Endpoints** | All services accessible only via private IPs |
| **Network Isolation** | VNet with delegated subnet for agent runtime |
| **No Public Access** | `publicNetworkAccess: Disabled` on all resources |
| **Managed Identity** | System-assigned identity for RBAC |
| **Local Auth Disabled** | Cosmos DB uses AAD only |
| **TLS 1.2** | Minimum TLS version enforced |

## 🗂️ File Structure

```
infra/
├── README.md                    # This file
├── main.bicep                   # Main orchestration template
├── main.bicepparam              # Parameter values
├── deleteCapHost.sh             # Cleanup script for capability host
└── modules-network-secured/     # Bicep modules
    ├── ai-account-identity.bicep
    ├── ai-project-identity.bicep
    ├── ai-search-role-assignments.bicep
    ├── add-project-capability-host.bicep
    ├── azure-storage-account-role-assignment.bicep
    ├── blob-storage-container-role-assignments.bicep
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
az group delete --name rg-talentreconnect-prod --yes --no-wait
```

## 📊 Current Deployment

**Resource Group:** `rg-talentreconnect-sweden`  
**Location:** Sweden Central  
**Deployed:** January 30, 2026

| Resource | Name |
|----------|------|
| AI Foundry Account | `tragt4pwr` |
| AI Foundry Project | `trproj4pwr` |
| Capability Host | `caphostproj` |
| Cosmos DB | `tragt4pwrcosmosdb` |
| AI Search | `tragt4pwrsearch` |
| Storage | `tragt4pwrstorage` |
| VNet | `talentreconnect-vnet` |

### Endpoints

| Service | Endpoint |
|---------|----------|
| AI Foundry | `https://tragt4pwr.cognitiveservices.azure.com/` |
| Cosmos DB | `https://tragt4pwrcosmosdb.documents.azure.com:443/` |
| AI Search | Private only (via VNet) |
| Storage | Private only (via VNet) |

## 🔗 Related Documentation

- [Azure AI Foundry Agent Service](https://learn.microsoft.com/azure/ai-foundry/agents/)
- [Standard Agent Setup](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/standard-agent-setup)
- [Network Isolation](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/virtual-network)
- [Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
