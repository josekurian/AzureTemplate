// Azure AI Document Intelligence Module
// AI-102: Extracts structured fields from menus, invoices, supplier forms.
//         Pre-built models (invoice, receipt) require no training data.

param name string
param location string
param managedIdentityPrincipalId string
param logAnalyticsWorkspaceId string
param tags object

resource docIntelligence 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: 'FormRecognizer'  // Document Intelligence resource kind
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
  }
}

// RBAC: Cognitive Services User — allows API inference calls
var cogServicesUserRoleId = 'a97b65f3-24c7-4dca-a6e1-deab48c82f6a'
resource docIntRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(docIntelligence.id, managedIdentityPrincipalId, cogServicesUserRoleId)
  scope: docIntelligence
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cogServicesUserRoleId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic Settings for page-level error tracking
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'docint-diagnostics'
  scope: docIntelligence
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [
      { category: 'AllMetrics'; enabled: true; retentionPolicy: { enabled: true; days: 30 } }
    ]
  }
}

output endpoint string = docIntelligence.properties.endpoint
output accountId string = docIntelligence.id
