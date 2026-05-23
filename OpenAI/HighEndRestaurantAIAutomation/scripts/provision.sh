#!/usr/bin/env bash
set -euo pipefail
RESOURCE_GROUP=${RESOURCE_GROUP:-rg-restaurant-ai-dev}
LOCATION=${LOCATION:-eastus}
APP_NAME=${APP_NAME:-restaurant-ai-dev}
az group create -n "$RESOURCE_GROUP" -l "$LOCATION"
az deployment group create -g "$RESOURCE_GROUP" -f infra/bicep/main.bicep -p location="$LOCATION" appName="$APP_NAME"
