using './main.bicep'

// ============================================================================
// Talent Reconnect Agent - Deployment Parameters
// ============================================================================

// Base name used as prefix for all resources
param baseName = 'talentreconnect'

// Azure region (choose based on model availability and latency)
// Options: eastus, eastus2, westus2, westeurope, swedencentral, uaenorth, etc.
param location = 'uaenorth'

// Environment tag
param environment = 'dev'

// Deploy Application Insights for observability
param deployAppInsights = true

// Azure AI Search SKU
// - 'basic': ~$75/mo, good for small demos
// - 'standard': ~$250/mo, recommended for production features
param searchSku = 'standard'
