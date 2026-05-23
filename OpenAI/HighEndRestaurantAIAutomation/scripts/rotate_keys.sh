#!/usr/bin/env bash
set -euo pipefail
RESOURCE_GROUP=${RESOURCE_GROUP:-rg-restaurant-ai-dev}
ACCOUNT_NAME=${ACCOUNT_NAME:-restaurant-ai-dev-aiservices}
KEY_NAME=${KEY_NAME:-key1}

az cognitiveservices account keys regenerate \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --key-name "$KEY_NAME"

echo "Regenerated $KEY_NAME for $ACCOUNT_NAME. Update Key Vault and switch clients after validation."
