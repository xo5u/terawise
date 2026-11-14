from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Field Shift Backend"
    DEBUG: bool = False
    DATABASE_URL: str = ""
    SECRET_KEY: str = "change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
