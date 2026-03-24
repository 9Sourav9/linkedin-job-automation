from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Anthropic
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-sonnet-4-6", alias="ANTHROPIC_MODEL")

    # Storage
    storage_path: str = Field("./storage", alias="STORAGE_PATH")

    # App
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    api_v1_prefix: str = Field("/api/v1", alias="API_V1_PREFIX")

    # Scraper
    scraper_headless: bool = Field(True, alias="SCRAPER_HEADLESS")
    scraper_delay_min: float = Field(2.0, alias="SCRAPER_DELAY_MIN")
    scraper_delay_max: float = Field(5.0, alias="SCRAPER_DELAY_MAX")


settings = Settings()
