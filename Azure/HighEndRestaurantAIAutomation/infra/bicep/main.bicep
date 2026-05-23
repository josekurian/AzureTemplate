@description('Main deployment for HighEndRestaurantAIAutomation resources')
param location string = 'eastus'

// Modules
module redisModule 'redis.bicep' = {
  name: 'redisModule'
  params: {
    redisName: 'restaurant-redis'
    location: location
  }
}

module searchModule 'search.bicep' = {
  name: 'searchModule'
  params: {
    searchServiceName: 'restaurant-search'
    location: location
  }
}

module functionsModule 'functions.bicep' = {
  name: 'functionsModule'
  params: {
    functionAppName: 'restaurant-func-app'
    location: location
  }
}

output redisHost string = redisModule.outputs.redisHost
output searchServiceName string = searchModule.outputs.searchServiceName
output functionAppName string = functionsModule.outputs.functionAppName
