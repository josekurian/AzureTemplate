param location string = resourceGroup().location
param appName string = 'restaurant-ai-dev'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${appName}-law'
  location: location
  properties: { sku: { name: 'PerGB2018' } retentionInDays: 30 }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${appName}-appi'
  location: location
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: logAnalytics.id }
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${take(appName, 16)}-kv'
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
  }
}

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: '${appName}-search'
  location: location
  sku: { name: 'basic' }
  properties: { replicaCount: 1, partitionCount: 1, hostingMode: 'default' }
}

resource openai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${appName}-openai'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

resource aiServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${appName}-aiservices'
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: toLower(replace('${take(appName, 16)}st', '-', ''))
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: { allowBlobPublicAccess: false }
}

output keyVaultUri string = kv.properties.vaultUri
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output openAIEndpoint string = openai.properties.endpoint
output aiServicesEndpoint string = aiServices.properties.endpoint
output appInsightsConnectionString string = appInsights.properties.ConnectionString
