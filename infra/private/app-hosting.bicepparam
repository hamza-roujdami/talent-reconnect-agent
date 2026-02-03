using './app-hosting.bicep'

// Talent Reconnect - App Hosting Parameters (Sweden Central)
// Deploys APIM (AI Gateway) + Container Apps

param location = 'swedencentral'
param environment = 'prod'
param namePrefix = 'tragt'

// API Management configuration
param publisherEmail = 'admin@talentreconnect.ai'
param publisherName = 'Talent Reconnect'
param apimSku = 'Basicv2'  // Basicv2 for production, Developer for dev/test

// VNet integration - Use the dedicated app-subnet (NOT agent-subnet!)
// The agent-subnet is exclusively for AI Foundry's internal Container Apps
// Our FastAPI app needs its own subnet delegated to Microsoft.App/environments
param containerAppsSubnetId = '/subscriptions/8374e213-686f-4d26-8287-80f53900cddc/resourceGroups/rg-talentreconnect-sweden/providers/Microsoft.Network/virtualNetworks/talentreconnect-vnet/subnets/app-subnet'

// AI Foundry endpoint (from main.bicep deployment)
// Get with: az cognitiveservices account show -g rg-talentreconnect-sweden -n tragt4pwr --query properties.endpoint -o tsv
param aiFoundryEndpoint = 'https://tragt4pwr.cognitiveservices.azure.com/'

param tags = {
  project: 'talent-reconnect-agent'
  environment: 'prod'
  component: 'app-hosting'
}
