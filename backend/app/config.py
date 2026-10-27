"""Application settings, read from environment variables or backend/.env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Mode: "mock" never calls a paid API. "live" uses the real providers.
    app_mode: Literal["mock", "live"] = "mock"

    # Provider credentials (backend only, never sent to the browser).
    openai_api_key: str = ""
    openai_model: str = "gpt-6.1-terra"
    google_maps_api_key: str = ""

    # Network
    frontend_origin: str = "http://localhost:5288"
    request_timeout_seconds: float = 90.0
    max_retries: int = 1  # extra attempts after the first; each attempt is budgeted

    # Uploads
    max_upload_mb: float = 10.0
    max_images_per_request: int = 12
    min_image_side_px: int = 480
    api_image_max_side_px: int = 1600  # images are downscaled before being sent to the AI provider

    # Per-assessment limits (kept in memory only)
    max_calls_per_assessment: int = 12
    max_tokens_per_assessment: int = 250_000
    max_output_tokens: int = 4_000
    max_web_search_calls: int = 6  # per price research request

    # Project budget (THB). PRIOR_SPEND_THB is spend outside this app, which the app cannot see.
    project_budget_thb: float = 4000.0
    prior_spend_thb: float = 0.0
    usd_to_thb: float = 35.0  # assumption: update to your card's actual rate

    # Pricing assumptions (USD). Verify against current provider pricing pages.
    openai_input_usd_per_1m: float = 1.00
    openai_output_usd_per_1m: float = 5.00
    openai_web_search_usd_per_1k: float = 10.00
    estimated_tokens_per_image: int = 2_500
    estimated_search_content_tokens: int = 8_000  # per search call, billed as input tokens
    places_include_contact_fields: bool = True  # phone/website => Enterprise SKU
    places_pro_usd_per_1k: float = 32.00
    places_enterprise_usd_per_1k: float = 35.00

    usage_ledger_path: Path = BACKEND_DIR / "data" / "usage_ledger.jsonl"

    @field_validator("usage_ledger_path")
    @classmethod
    def _relative_to_backend(cls, value: Path) -> Path:
        return value if value.is_absolute() else BACKEND_DIR / value

    @property
    def is_mock(self) -> bool:
        return self.app_mode == "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
