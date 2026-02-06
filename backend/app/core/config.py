from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    project_name: str = ""
    database_url: str = ""
    redis_url: str = ""
    secret_key: str = ""
    
    # Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@smsgateway.com"
    frontend_url: str = "http://localhost:5173"

    model_config = {
        "env_file": ".env",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
