"""
Environment configuration.

Loaded once at import time. Any missing required key raises immediately
so the error surfaces at startup, not mid-request.

Usage:
    from backend.config import settings
    client = OpenAI(api_key=settings.openai_api_key)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


TextLLMProvider   = Literal["openai", "gemini"]
VisionLLMProvider = Literal["openai", "qwen_local"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM keys ─────────────────────────────────────────────────────
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # ── Provider selection ────────────────────────────────────────────
    text_llm_provider:   TextLLMProvider   = "openai"
    vision_llm_provider: VisionLLMProvider = "openai"

    # ── Model overrides ───────────────────────────────────────────────
    text_model:   str = "gpt-4o-mini"
    vision_model: str = "gpt-4o"

    # ── Server ────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── Validators ───────────────────────────────────────────────────
    @model_validator(mode="after")
    def _require_keys_for_providers(self) -> "Settings":
        if self.text_llm_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "TEXT_LLM_PROVIDER=openai but OPENAI_API_KEY is not set in .env"
            )
        if self.text_llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "TEXT_LLM_PROVIDER=gemini but GEMINI_API_KEY is not set in .env"
            )
        if self.vision_llm_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "VISION_LLM_PROVIDER=openai but OPENAI_API_KEY is not set in .env"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance. Call once, reuse everywhere."""
    return Settings()


# Module-level singleton — import this directly
settings = get_settings()
