from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = Field(default=os.getenv("ENV", "development"))
    app_host: str = Field(default=os.getenv("APP_HOST", "0.0.0.0"))
    app_port: int = Field(default=int(os.getenv("APP_PORT", "8000")))

    default_timezone: str = Field(default=os.getenv("DEFAULT_TIMEZONE", "UTC"))
    storage_dir: str = Field(default=os.getenv("STORAGE_DIR", os.path.abspath(os.path.join(os.getcwd(), "data"))))

    database_url: str = Field(default=os.getenv("DATABASE_URL", f"sqlite:///{os.path.abspath(os.path.join(os.getcwd(), 'data', 'app.db'))}"))

    twilio_account_sid: Optional[str] = Field(default=os.getenv("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: Optional[str] = Field(default=os.getenv("TWILIO_AUTH_TOKEN"))
    twilio_whatsapp_number: Optional[str] = Field(default=os.getenv("TWILIO_WHATSAPP_NUMBER"))
    public_base_url: Optional[str] = Field(default=os.getenv("PUBLIC_BASE_URL"))

    mem0_api_key: Optional[str] = Field(default=os.getenv("MEM0_API_KEY"))

    openai_api_key: Optional[str] = Field(default=os.getenv("OPENAI_API_KEY"))

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[arg-type]
    os.makedirs(settings.storage_dir, exist_ok=True)
    # Ensure parent dir for sqlite db exists if sqlite is used
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("sqlite:///")[-1]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return settings 