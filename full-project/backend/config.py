from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./parkinsense.db"
    # JWT
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # App
    APP_NAME: str = "AI-Powered Parkinson's Monitoring System"
    # Allow both string and bool to avoid failures on malformed env values;
    # we'll coerce to bool after construction.
    DEBUG: str | bool = False
    UPLOAD_DIR: str = "uploads"
    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
settings = Settings()
# Coerce DEBUG to bool (accepts 'true','1','yes', etc.)
if isinstance(settings.DEBUG, str):
    settings.DEBUG = settings.DEBUG.lower() in ("1", "true", "yes", "on")

# If SECRET_KEY or DATABASE_URL are still placeholders, we'll keep them for
# development, but the application startup checks will warn or raise as
# appropriate when the server is run.