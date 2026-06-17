from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration - loads all settings from .env file."""
    
    # Database connection parameters
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    
    # Key used by Flask for signing session cookies securely
    secret_key: str
    
    # Spoonacular API settings for recipe/ingredient searching
    spoonacular_api_key: str
    spoonacular_url: str
    
    # URL for AI recipe generator service
    ai_url: str
    
    # Configure Pydantic to read from .env and ignore any unrecognized/extra fields
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Global settings instance - use this to access all config values
settings = Settings()