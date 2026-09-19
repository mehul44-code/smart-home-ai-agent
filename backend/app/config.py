import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Autonomous Smart Home Energy & Comfort AI Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # SQLite Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./smart_home.db"
    SYNC_DATABASE_URL: str = "sqlite:///./smart_home.db"

    # Simulation settings
    SIMULATION_STEP_INTERVAL_SEC: float = 2.0
    TIME_ACCELERATION_FACTOR: int = 60
    BASE_TARGET_TEMP_C: float = 22.0
    TEMP_COMFORT_TOLERANCE_C: float = 1.5
    PEAK_TARIFF_THRESHOLD: float = 0.25

    # Models
    MODELS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "models")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
