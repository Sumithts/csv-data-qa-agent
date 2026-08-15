"""Application configuration, validated with pydantic-settings.

All secrets/settings come from environment variables or a `.env` file —
never hard-coded. Using BaseSettings (instead of raw os.getenv calls)
gives us free validation: e.g. MAX_CODEGEN_RETRIES must be a non-negative
int, or the app fails fast at startup with a clear message rather than
failing confusingly three calls deep.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the CSV Q&A Agent.

    Read from environment variables / a `.env` file at the project root.
    See `.env.example` for the full list of supported keys.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = Field(default="", description="Groq API key (console.groq.com/keys)")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    max_codegen_retries: int = Field(default=2, ge=0, le=5)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    request_timeout_seconds: int = Field(default=30, gt=0)

    default_csv_path: Path = Field(default=Path("data/sales_data.csv"))

    log_level: str = Field(default="INFO")

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got {v!r}")
        return v_upper

    def require_groq_key(self) -> str:
        """Returns the Groq API key or raises ConfigurationError with a helpful message."""
        from .exceptions import ConfigurationError  # local import avoids a cycle

        if not self.groq_api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
                "free key from https://console.groq.com/keys"
            )
        return self.groq_api_key


# Module-level singleton — imported as `from src.config import settings`
settings = Settings()
