// Log Analytics Workspace Module
// AI-102: Central destination for all diagnostic settings across AI resources.
//         Enables KQL queries for latency, errors, token usage, content safety.

param name string
param location string
param tags object

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'   // Pay-per-GB — cost driver: log volume
    }
    retentionInDays: 90   // AI-102: Balance compliance with cost
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

output workspaceId string = logAnalyticsWorkspace.id
output workspaceName string = logAnalyticsWorkspace.name
output customerId string = logAnalyticsWorkspace.properties.customerId
