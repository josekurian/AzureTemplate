from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mock_mode: bool = True
    app_env: str = "dev"
    log_level: str = "INFO"
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "gpt4o-restaurant"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-02-01"
    azure_search_endpoint: str = ""
    azure_search_index: str = "restaurant-knowledge-index"
    azure_language_endpoint: str = ""
    azure_translator_endpoint: str = ""
    azure_speech_region: str = "eastus"
    azure_content_safety_endpoint: str = ""
    azure_document_intelligence_endpoint: str = ""
    azure_vision_endpoint: str = ""
    key_vault_uri: str = ""
    applicationinsights_connection_string: str = ""

settings = Settings()
