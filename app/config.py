from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration - loads all settings from .env file."""
    # Database connection settings
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    # JWT authentication settings
    secret_key: str
    algorithm: str
    # Spoonacular API settings for recipe/ingredient searching
    spoonacular_api_key: str
    spoonacular_url: str
    ai_url:str
    backend_url: str
    
    model_config = SettingsConfigDict(env_file=".env")


# Global settings instance - use this to access all config values
settings = Settings()