param location string = resourceGroup().location
param searchServiceName string = 'restaurant-search'
param sku string = 'basic'
param semanticSearch string = 'free'
param replicaCount int = 1
param partitionCount int = 1

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  sku: {
    name: sku
  }
  properties: {
    hostingMode: 'default'
    replicaCount: replicaCount
    partitionCount: partitionCount
    semanticSearch: semanticSearch
    publicNetworkAccess: 'enabled'
    disableLocalAuth: false
  }
}

output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
