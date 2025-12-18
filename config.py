from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str
    ADMIN_ID: int
    API_ID: int
    API_HASH: str

    DATA_FILE: str = "data.json"
    MAX_MESSAGES_PER_REQUEST: int = 100
    HISTORY_MESSAGES_LIMIT: int = 5000
    BATCH_DELAY: float = 1.0


settings = Settings()