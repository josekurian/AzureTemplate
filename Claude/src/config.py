"""
config.py — Centralised configuration for Restaurant AI Assistant
=================================================================
AI-102 Exam Skills Demonstrated:
  - Secure configuration: all secrets from environment / Key Vault
  - DefaultAzureCredential: Managed Identity in Azure, CLI locally
  - No hardcoded keys, no plaintext secrets in code
"""

import os
from dataclasses import dataclass
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@dataclass
class RestaurantAIConfig:
    # Azure OpenAI
    openai_endpoint: str
    openai_chat_deployment: str
    openai_embedding_deployment: str
    openai_api_version: str = "2024-02-01"

    # Azure AI Search
    search_endpoint: str
    search_index_name: str = "restaurant-knowledge"

    # Azure AI Document Intelligence
    doc_intelligence_endpoint: str

    # Azure AI Content Safety
    content_safety_endpoint: str

    # Azure Storage
    storage_account_name: str
    storage_container_name: str = "restaurant-documents"

    # Monitoring
    appinsights_connection_string: str

    # Identity
    managed_identity_client_id: str = ""


def load_config() -> RestaurantAIConfig:
    """
    Load configuration from environment variables.
    In Azure (App Service / Container Apps), these are set from Key Vault
    references or Bicep outputs injected at deployment time.
    Locally, set them in a .env file (never commit .env to source control).
    """
    return RestaurantAIConfig(
        openai_endpoint=_require("AZURE_OPENAI_ENDPOINT"),
        openai_chat_deployment=_require("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_embedding_deployment=_require("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        search_endpoint=_require("AZURE_SEARCH_ENDPOINT"),
        search_index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "restaurant-knowledge"),
        doc_intelligence_endpoint=_require("AZURE_DOC_INTELLIGENCE_ENDPOINT"),
        content_safety_endpoint=_require("AZURE_CONTENT_SAFETY_ENDPOINT"),
        storage_account_name=_require("AZURE_STORAGE_ACCOUNT_NAME"),
        storage_container_name=os.getenv("AZURE_STORAGE_CONTAINER", "restaurant-documents"),
        appinsights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
        managed_identity_client_id=os.getenv("AZURE_CLIENT_ID", ""),  # User-assigned MI client ID
    )


def get_credential() -> DefaultAzureCredential:
    """
    Returns DefaultAzureCredential.
    Resolution order:
      1. EnvironmentCredential (CI/CD service principal)
      2. ManagedIdentityCredential (Azure App Service / Container Apps)
      3. AzureCliCredential (local developer machine after 'az login')
    AI-102: This single call works in dev AND prod — no code change needed.
    """
    client_id = os.getenv("AZURE_CLIENT_ID")
    if client_id:
        # User-assigned Managed Identity: must pass client_id explicitly
        from azure.identity import ManagedIdentityCredential
        return ManagedIdentityCredential(client_id=client_id)
    return DefaultAzureCredential()


def _require(env_var: str) -> str:
    value = os.getenv(env_var)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{env_var}' is not set. "
            "Set it in your .env file (local) or App Service configuration (Azure)."
        )
    return value
