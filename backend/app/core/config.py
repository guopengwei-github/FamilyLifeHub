"""
Core configuration module for FamilyLifeHub backend.
Loads environment variables and provides application settings.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Union, List, Optional


def get_default_data_dir() -> Path:
    """获取默认数据目录（跨平台支持）"""
    if os.name == 'nt':  # Windows
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:  # Linux/macOS
        base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    return Path(base) / 'family_life_hub'


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "FamilyLifeHub"
    debug: bool = True

    # Database - 支持直接指定 DATABASE_URL 或使用 DATA_DIR
    database_url: Optional[str] = None
    data_dir: str = str(get_default_data_dir())

    # Security
    api_key: str = "your-secret-api-key-change-this-in-production"
    secret_key: str = "your-jwt-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS
    allowed_origins: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:3001"]

    # Zhipu LLM Configuration
    zhipu_api_key: str = ""
    zhipu_model: str = "glm-4-flash"
    report_retry_max: int = 3
    report_retry_intervals: str = "1,4,12"  # hours

    @property
    def database_path(self) -> str:
        """获取数据库连接字符串，优先使用 DATABASE_URL，否则使用 DATA_DIR"""
        if self.database_url:
            return self.database_url
        data_path = Path(self.data_dir)
        data_path.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{data_path / 'family_life_hub.db'}"

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
