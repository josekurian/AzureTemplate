# Infrastructure

Use Bicep to deploy resources for AI-102 practice. The files are intentionally readable and Codex-friendly.

Deploy example:

```bash
az group create -n rg-restaurant-ai-dev -l eastus
az deployment group create -g rg-restaurant-ai-dev -f infra/bicep/main.bicep -p location=eastus appName=restaurant-ai-dev
```

After deployment, assign managed identity roles and update app settings.
