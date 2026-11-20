from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    project_name: str = "Voche App"
    database_url: str = ""
    redis_url: str = ""
    secret_key: str = "unsafe_secret_key"
    access_token_expire_minutes: int = 60

    # Google sign-in: the OAuth Client ID (public, the same one the frontend uses)
    google_client_id: str = ""

    # Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    frontend_url: str = "http://localhost:5173"
    frontend_var: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"]

<<<<<<< HEAD
    # Private file storage: "local" (development) or "s3" (Amazon S3, Cloudflare R2, Supabase Storage)
    storage_backend: str = "local"
    private_uploads_dir: str = "private_uploads"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
=======
    # AI Assistant (empty key = offline answers that list matching trials/resources)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    # ClinicalTrials.gov sync (off by default so local runs and tests never call the API)
    trial_sync_enabled: bool = False
    trial_sync_conditions: str = "HIV,Tuberculosis,Malaria"
    trial_sync_max_per_condition: int = 100
>>>>>>> origin/feature/phase2-ai-chatbot-trials-surveys

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()