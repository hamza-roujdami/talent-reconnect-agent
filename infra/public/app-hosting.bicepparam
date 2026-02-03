using 'app-hosting.bicep'

param location = 'swedencentral'
param namePrefix = 'tragt'
param publisherEmail = 'admin@talentreconnect.ai'
param publisherName = 'Talent Reconnect'
param apimSku = 'Consumption'

// Fill this after deploying main.bicep
param aiFoundryEndpoint = ''
