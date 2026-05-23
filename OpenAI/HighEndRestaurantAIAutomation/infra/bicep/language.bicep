param location string = resourceGroup().location
param appName string = 'restaurant-ai-dev'

resource aiServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${appName}-aiservices'
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

resource speech 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${appName}-speech'
  location: location
  kind: 'SpeechServices'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

output aiServicesEndpoint string = aiServices.properties.endpoint
output speechEndpoint string = speech.properties.endpoint
