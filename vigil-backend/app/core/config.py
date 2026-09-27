from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "VIGIL Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = ""

    GITHUB_APP_ID: str = ""
    GITHUB_PRIVATE_KEY: str = ""
    GITHUB_PRIVATE_KEY_PATH: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_API_BASE_URL: str = "https://api.github.com"

    # CORS configuration - default to open for local development
    CORS_ORIGINS: list[str] = ["*"]

    # AI Config
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama3-8b-8192"
    LLM_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
