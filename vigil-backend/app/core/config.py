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

    # ── Legacy AI config (used only by the dormant GroqProvider / provider.py path) ──
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama3-8b-8192"
    LLM_API_KEY: str = ""

    # ── Active AI config (read by OpenAICompatibleProvider → AIModelGateway pipeline) ──
    # Set AI_API_KEY to your Google AI Studio API key.
    # Set AI_BASE_URL to https://generativelanguage.googleapis.com/v1beta/openai/
    # Set AI_MODEL to gemini-3.8-flash
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    AI_MODEL: str = "gemini-3.8-flash"
    AI_TIMEOUT_SECONDS: float = 60.0
    AI_MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
