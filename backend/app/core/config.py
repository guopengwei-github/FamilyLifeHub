"""
Core configuration module for FamilyLifeHub backend.
Loads environment variables and provides application settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Union, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "FamilyLifeHub"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./family_life_hub.db"

    # Security
    api_key: str = "your-secret-api-key-change-this-in-production"
    secret_key: str = "your-jwt-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS
    allowed_origins: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:3001"]

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse comma-separated string into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
