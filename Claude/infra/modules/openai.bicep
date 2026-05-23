// Azure OpenAI Service Module
// AI-102: Deploys chat completion + embedding models; configures content filters;
//         grants Managed Identity the 'Cognitive Services OpenAI User' role.

param name string
param location string
param modelName string
param embeddingModelName string
param capacity int
param managedIdentityPrincipalId string
param logAnalyticsWorkspaceId string
param tags object

// ── Azure OpenAI Account ──────────────────────────────────────────────────────
resource openAiAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'  // Use 'Disabled' + private endpoint for prod
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// ── Chat Model Deployment ─────────────────────────────────────────────────────
resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAiAccount
  name: '${modelName}-chat'
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: '2024-08-06'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    // AI-102: Content filter policy applied here
    raiPolicyName: 'restaurant-content-filter'
  }
  sku: {
    name: 'Standard'
    capacity: capacity
  }
}

// ── Embedding Model Deployment ────────────────────────────────────────────────
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAiAccount
  name: '${embeddingModelName}-embed'
  dependsOn: [chatDeployment]
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: '1'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
  sku: {
    name: 'Standard'
    capacity: capacity
  }
}

// ── RBAC: Managed Identity → Cognitive Services OpenAI User ──────────────────
// AI-102: Least-privilege role; allows inference calls, not key management
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource openAiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAiAccount.id, managedIdentityPrincipalId, openAiUserRoleId)
  scope: openAiAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ── Diagnostic Settings → Log Analytics ──────────────────────────────────────
// AI-102: Captures token usage, latency, content filter decisions
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'openai-diagnostics'
  scope: openAiAccount
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { category: 'Audit'; enabled: true; retentionPolicy: { enabled: true; days: 90 } }
      { category: 'RequestResponse'; enabled: true; retentionPolicy: { enabled: true; days: 30 } }
    ]
    metrics: [
      { category: 'AllMetrics'; enabled: true; retentionPolicy: { enabled: true; days: 30 } }
    ]
  }
}

output endpoint string = openAiAccount.properties.endpoint
output accountId string = openAiAccount.id
output chatDeploymentName string = chatDeployment.name
output embeddingDeploymentName string = embeddingDeployment.name
