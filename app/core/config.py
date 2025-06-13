from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache # For caching the settings instance

class Settings(BaseSettings):
    """
    Application settings.
    Values are loaded from environment variables and/or a .env file.
    """
    GOOGLE_API_KEY: str = "FALLBACK_GOOGLE_API_KEY"
    APP_NAME: str = "Deep Chain Graph"
    DEFAULT_LLM_MODEL: str = "MODEL_NAME"

    # Configure Pydantic to load from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

@lru_cache()
def get_settings() -> Settings:
    """
    Returns the application settings.
    The settings are loaded from environment variables and the .env file.
    The instance is cached so the .env file is read only once.
    """
    return Settings()
