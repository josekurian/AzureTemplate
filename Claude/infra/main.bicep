// =============================================================================
// Restaurant AI Automation — Azure AI-102 Sample Implementation
// main.bicep  — Orchestrator: deploys all modules
// =============================================================================
// Author  : Jose Kurian (jose@hybridgenai.com)
// Purpose : AI-102 exam hands-on project — High-End Restaurant AI Assistant
// =============================================================================

targetScope = 'resourceGroup'

// ── Parameters ────────────────────────────────────────────────────────────────
@description('Base name used as prefix for all resources')
param baseName string = 'restaurantai'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Environment tag: dev | staging | prod')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure OpenAI model to deploy (gpt-4o recommended)')
param openAiModelName string = 'gpt-4o'

@description('Model deployment capacity in TPM thousands')
param openAiCapacity int = 10

@description('Azure OpenAI embedding model name')
param embeddingModelName string = 'text-embedding-3-large'

@description('Object ID of the user/group to grant initial Key Vault access')
param adminObjectId string

// ── Variables ─────────────────────────────────────────────────────────────────
var prefix = '${baseName}-${environment}'
var tags = {
  project: 'restaurant-ai'
  environment: environment
  'ai102-exam': 'true'
  owner: 'jose@hybridgenai.com'
  costCenter: 'restaurant-ops'
}

// ── Modules ───────────────────────────────────────────────────────────────────

// 1. Managed Identity (created first — other modules reference its principal ID)
module identity 'modules/identity.bicep' = {
  name: 'identity-deploy'
  params: {
    name: '${prefix}-identity'
    location: location
    tags: tags
  }
}

// 2. Log Analytics Workspace (created before App Insights)
module logAnalytics 'modules/loganalytics.bicep' = {
  name: 'loganalytics-deploy'
  params: {
    name: '${prefix}-logs'
    location: location
    tags: tags
  }
}

// 3. Application Insights (depends on Log Analytics)
module appInsights 'modules/appinsights.bicep' = {
  name: 'appinsights-deploy'
  params: {
    name: '${prefix}-insights'
    location: location
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    tags: tags
  }
}

// 4. Storage Account (blob for PDFs/menus/training data)
module storage 'modules/storage.bicep' = {
  name: 'storage-deploy'
  params: {
    name: '${replace(prefix, '-', '')}stor'
    location: location
    managedIdentityPrincipalId: identity.outputs.principalId
    tags: tags
  }
}

// 5. Key Vault (secrets for any non-MI scenarios)
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault-deploy'
  params: {
    name: '${prefix}-kv'
    location: location
    adminObjectId: adminObjectId
    managedIdentityPrincipalId: identity.outputs.principalId
    tags: tags
  }
}

// 6. Azure OpenAI Service
module openAi 'modules/openai.bicep' = {
  name: 'openai-deploy'
  params: {
    name: '${prefix}-openai'
    location: location
    modelName: openAiModelName
    embeddingModelName: embeddingModelName
    capacity: openAiCapacity
    managedIdentityPrincipalId: identity.outputs.principalId
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    tags: tags
  }
}

// 7. Azure AI Search
module search 'modules/search.bicep' = {
  name: 'search-deploy'
  params: {
    name: '${prefix}-search'
    location: location
    managedIdentityPrincipalId: identity.outputs.principalId
    tags: tags
  }
}

// 8. Azure AI Document Intelligence
module docIntelligence 'modules/docintelligence.bicep' = {
  name: 'docintelligence-deploy'
  params: {
    name: '${prefix}-docint'
    location: location
    managedIdentityPrincipalId: identity.outputs.principalId
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    tags: tags
  }
}

// 9. Azure AI Content Safety
module contentSafety 'modules/contentsafety.bicep' = {
  name: 'contentsafety-deploy'
  params: {
    name: '${prefix}-safety'
    location: location
    managedIdentityPrincipalId: identity.outputs.principalId
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    tags: tags
  }
}

// ── Outputs (used by app configuration and CI/CD pipelines) ───────────────────
output openAiEndpoint string = openAi.outputs.endpoint
output searchEndpoint string = search.outputs.endpoint
output docIntelligenceEndpoint string = docIntelligence.outputs.endpoint
output contentSafetyEndpoint string = contentSafety.outputs.endpoint
output storageAccountName string = storage.outputs.storageAccountName
output keyVaultUri string = keyVault.outputs.keyVaultUri
output appInsightsConnectionString string = appInsights.outputs.connectionString
output logAnalyticsWorkspaceId string = logAnalytics.outputs.workspaceId
output managedIdentityClientId string = identity.outputs.clientId
output openAiChatDeploymentName string = openAi.outputs.chatDeploymentName
output openAiEmbeddingDeploymentName string = openAi.outputs.embeddingDeploymentName
