from fastapi import APIRouter

from ..config import get_settings
from ..fixtures.mock_data import MOCK_SCENARIOS
from ..services.usage_tracking import get_tracker

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health():
    """Readiness without secrets. 'configured' means a key is present, not that it works."""
    s = get_settings()
    return {
        "status": "ok",
        "mode": s.app_mode,
        "openai": {
            "key_configured": bool(s.openai_api_key),
            "model": s.openai_model,
            "connection_verified": False,
        },
        "google_places": {"key_configured": bool(s.google_maps_api_key), "connection_verified": False},
        "mock_scenarios": MOCK_SCENARIOS if s.is_mock else {},
        "limits": {
            "max_upload_mb": s.max_upload_mb,
            "max_images_per_request": s.max_images_per_request,
            "min_image_side_px": s.min_image_side_px,
            "max_calls_per_assessment": s.max_calls_per_assessment,
            "max_tokens_per_assessment": s.max_tokens_per_assessment,
        },
        "notes": [
            "Mock mode makes no paid API calls." if s.is_mock else "Live mode: provider calls are billed by the providers.",
            "Run the live smoke test (docs/SETUP.md) to verify connections.",
        ],
    }


@router.get("/usage")
def usage():
    return get_tracker().summary()
