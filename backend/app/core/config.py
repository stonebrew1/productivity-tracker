from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://productivity:productivity@localhost:5432/productivity"
    secret_key: str = "local-development-secret-change-in-production"
    algorithm: str = "HS256"
    jwt_issuer: str = "momentum-api"
    jwt_audience: str = "momentum-web"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    refresh_cookie_secure: bool = False
    refresh_cookie_name: str = "momentum_refresh"
    frontend_origin: str = "http://localhost:5173"
    email_verification_expire_hours: int = 24
    email_delivery_mode: str = "console"
    email_from: str = "Momentum <no-reply@momentum.local>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
