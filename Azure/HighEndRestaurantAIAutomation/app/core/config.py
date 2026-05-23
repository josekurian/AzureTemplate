from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MOCK_MODE: bool = True
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()
