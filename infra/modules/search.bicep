// Azure AI Search Service
// Supports semantic search and agentic retrieval for the recruiting agents

// ============================================================================
// Parameters
// ============================================================================

@description('Name of the search service')
param searchServiceName string

@description('Azure region')
param location string

@description('Search service SKU')
@allowed(['basic', 'standard', 'standard2', 'standard3'])
param sku string = 'standard'

@description('Resource tags')
param tags object = {}

@description('Number of replicas (for HA, use 2+ in production)')
@minValue(1)
@maxValue(12)
param replicaCount int = 1

@description('Number of partitions (for scale)')
@minValue(1)
@maxValue(12)
param partitionCount int = 1

// ============================================================================
// Azure AI Search Service
// ============================================================================

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // Replica and partition configuration
    replicaCount: replicaCount
    partitionCount: partitionCount
    
    // Hosting mode (default for standard SKUs)
    hostingMode: 'default'
    
    // Enable semantic search (required for agentic retrieval)
    semanticSearch: 'standard'
    
    // Network access (open for demo, use private endpoints for production)
    publicNetworkAccess: 'enabled'
    
    // Allow API key auth
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    
    // Disable local auth for production (uncomment below)
    // disableLocalAuth: true
  }
}

// ============================================================================
// Outputs
// ============================================================================

output name string = searchService.name
output id string = searchService.id
output endpoint string = 'https://${searchServiceName}.search.windows.net'
output principalId string = searchService.identity.principalId

// Note: API keys must be retrieved via Azure CLI or Portal after deployment
// az search admin-key show --resource-group <rg> --service-name <name>
