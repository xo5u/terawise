from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "Field Shift Backend"
    DEBUG: bool = False
    DATABASE_URL: str = ""
    SECRET_KEY: str = "change-me"

    # --- AI chatbot (OpenRouter) ---
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_WEB_SEARCH: bool = True
    OPENROUTER_SITE_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")


settings = Settings()