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

    ENTRA_TENANT_ID: str = ""
    ENTRA_API_CLIENT_ID: str = ""
    ENTRA_API_SCOPE: str = ""

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
