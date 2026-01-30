/*
  Network Security Parameters - Sweden Central
  
  Deploy with:
  az deployment group create \
    --resource-group rg-talentreconnect-sweden \
    --template-file infra/network-security.bicep \
    --parameters infra/network-security.bicepparam
*/
using 'network-security.bicep'

param location = 'swedencentral'
param namePrefix = 'tragt'
param vnetName = 'talentreconnect-vnet'
param appGwSubnetName = 'appgw-subnet'
param apimSubnetName = 'apim-subnet'

// Container App FQDN from existing deployment
param containerAppFqdn = 'tragt-ca-env-4pwr.swedencentral.azurecontainerapps.io'

// APIM Gateway FQDN
param apimGatewayFqdn = 'tragt-apim-4pwr.azure-api.net'

// WAF Configuration
param enableWaf = true
param wafMode = 'Prevention'
param appGwCapacity = 2

param tags = {
  project: 'talent-reconnect-agent'
  environment: 'production'
  component: 'network-security'
}
