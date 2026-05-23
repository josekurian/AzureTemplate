// Azure AI Content Safety Module
// AI-102: Screens user prompts AND model responses for hate/violence/sexual/self-harm.
//         Prompt Shields detect jailbreaks and indirect document injection attacks.

param name string
param location string
param managedIdentityPrincipalId string
param logAnalyticsWorkspaceId string
param tags object

resource contentSafety 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: 'ContentSafety'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
  }
}

// RBAC: Cognitive Services User role
var cogServicesUserRoleId = 'a97b65f3-24c7-4dca-a6e1-deab48c82f6a'
resource safetyRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(contentSafety.id, managedIdentityPrincipalId, cogServicesUserRoleId)
  scope: contentSafety
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cogServicesUserRoleId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic Settings — track blocked request rate by harm category
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'safety-diagnostics'
  scope: contentSafety
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [
      { category: 'AllMetrics'; enabled: true; retentionPolicy: { enabled: true; days: 90 } }
    ]
  }
}

output endpoint string = contentSafety.properties.endpoint
output accountId string = contentSafety.id
