// Key Vault Module
// AI-102: Stores any API keys that cannot use Managed Identity (e.g. third-party POS
//         webhook secrets). Managed Identity and admin user get least-privilege roles.

param name string
param location string
param adminObjectId string
param managedIdentityPrincipalId string
param tags object

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true   // AI-102: RBAC mode (not legacy access policies)
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true     // Prevents accidental permanent deletion
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// Admin user: Key Vault Administrator (full management)
var kvAdminRoleId = '00482a5a-887f-4fb3-b363-3b7fe8e74483'
resource adminRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, adminObjectId, kvAdminRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvAdminRoleId)
    principalId: adminObjectId
    principalType: 'User'
  }
}

// Managed Identity: Key Vault Secrets User (read-only secrets access)
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
resource miRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentityPrincipalId, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output keyVaultUri string = keyVault.properties.vaultUri
output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
