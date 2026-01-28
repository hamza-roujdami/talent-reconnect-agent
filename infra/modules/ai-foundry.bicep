// AI Foundry Account, Project, and Model Deployments
// Based on: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/create-resource-template

// ============================================================================
// Parameters
// ============================================================================

@description('Name of the AI Foundry account')
param aiFoundryName string

@description('Name of the AI Project')
param aiProjectName string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

// ============================================================================
// AI Foundry Account (Azure AI Services)
// ============================================================================

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiFoundryName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    // Required to work in AI Foundry portal
    allowProjectManagement: true
    // Custom subdomain for API endpoint
    customSubDomainName: aiFoundryName
    // Allow API key auth (can disable for production)
    disableLocalAuth: false
    // Network rules (open for demo, restrict for production)
    publicNetworkAccess: 'Enabled'
  }
}

// ============================================================================
// AI Project
// ============================================================================

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: aiProjectName
  parent: aiFoundry
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// ============================================================================
// Model Deployments
// ============================================================================

// Primary model: GPT-4o-mini (fast, cost-effective)
resource gpt4oMini 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiFoundry
  name: 'gpt-4o-mini'
  sku: {
    capacity: 10
    name: 'GlobalStandard'
  }
  properties: {
    model: {
      name: 'gpt-4o-mini'
      format: 'OpenAI'
      version: '2024-07-18'
    }
  }
}

// Secondary model: GPT-4o (more capable, for complex tasks)
resource gpt4o 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiFoundry
  name: 'gpt-4o'
  sku: {
    capacity: 5
    name: 'GlobalStandard'
  }
  properties: {
    model: {
      name: 'gpt-4o'
      format: 'OpenAI'
      version: '2024-08-06'
    }
  }
  dependsOn: [gpt4oMini] // Serial deployment to avoid conflicts
}

// Text embedding model for semantic search
resource textEmbedding 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiFoundry
  name: 'text-embedding-3-large'
  sku: {
    capacity: 10
    name: 'Standard'
  }
  properties: {
    model: {
      name: 'text-embedding-3-large'
      format: 'OpenAI'
      version: '1'
    }
  }
  dependsOn: [gpt4o] // Serial deployment to avoid conflicts
}

// ============================================================================
// Outputs
// ============================================================================

output name string = aiFoundry.name
output id string = aiFoundry.id
output endpoint string = 'https://${aiFoundryName}.openai.azure.com/'
output projectName string = aiProject.name
output projectId string = aiProject.id
output principalId string = aiFoundry.identity.principalId
