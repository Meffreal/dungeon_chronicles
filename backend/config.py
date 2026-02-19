"""
config.py — nastavení aplikace
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "dungeon-chronicles-super-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dní

    class Config:
        env_file = ".env"

settings = Settings()
