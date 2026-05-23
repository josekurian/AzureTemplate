// Azure AI Search Module
// AI-102: Standard tier enables semantic ranker + vector search for RAG retrieval.
//         Managed Identity granted 'Search Index Data Contributor' role.

param name string
param location string
param managedIdentityPrincipalId string
param tags object

resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'standard'  // Required for semantic ranking and vector search
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: 'standard'  // AI-102: Enables semantic ranker (per-query charge)
  }
}

// RBAC: Search Index Data Contributor — allows index read/write from app code
var searchIndexContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
resource searchRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, managedIdentityPrincipalId, searchIndexContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexContributorRoleId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output endpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceId string = searchService.id
output searchServiceName string = searchService.name
