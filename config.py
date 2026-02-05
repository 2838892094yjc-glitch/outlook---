from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # App
    APP_NAME: str = "Outlook Web Tool"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-this"

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/outlook_web"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    MICROSOFT_TENANT_ID: str = "common"  # common for personal accounts

    # AI Service
    AI_API_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4"

    # SMTP (Your Service)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
