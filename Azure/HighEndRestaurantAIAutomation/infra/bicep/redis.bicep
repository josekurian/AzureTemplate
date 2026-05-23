@description('Name for Redis cache')
param redisName string = 'restaurant-redis'
param location string = resourceGroup().location

resource redis 'Microsoft.Cache/Redis@2023-03-01' = {
  name: redisName
  location: location
  sku: {
    name: 'Standard'
    family: 'C'
    capacity: 1
  }
  properties: {
    enableNonSslPort: true
  }
}

output redisHost string = redis.properties.hostName
output redisPort int = redis.properties.port
