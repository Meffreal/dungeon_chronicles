"""
config.py — nastavení aplikace
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "dungeon-chronicles-super-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dní

    # Redis — volitelné; pokud není nastaven, používá se in-memory fallback
    # Příklad: redis://localhost:6379 nebo redis://:password@host:6379/0
    REDIS_URL: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
