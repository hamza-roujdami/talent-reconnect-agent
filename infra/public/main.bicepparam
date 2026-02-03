using 'main.bicep'

param location = 'uaenorth'
param aiServices = 'tragt'
param projectName = 'talent-reconnect'
param projectDescription = 'Talent Reconnect - AI Recruiting Assistant'

// Model configuration
param modelName = 'gpt-4o-mini'
param modelFormat = 'OpenAI'
param modelVersion = '2024-07-18'
param modelSkuName = 'GlobalStandard'
param modelCapacity = 40
