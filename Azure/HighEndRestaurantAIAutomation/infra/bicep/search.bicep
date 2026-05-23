@description('Cognitive Search scaffold')
param searchServiceName string = 'restaurant-search'
param location string = resourceGroup().location

resource search 'Microsoft.Search/searchServices@2020-08-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    hostingMode: 'default'
  }
}

output searchServiceName string = search.name
