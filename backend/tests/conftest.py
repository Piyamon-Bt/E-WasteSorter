import io
import random

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.config import get_settings
from app.schemas.physical import REQUIRED_VIEWS
from app.services.usage_tracking import get_tracker


@pytest.fixture
def configure(monkeypatch, tmp_path):
    """Sets environment-based settings for one test. Env vars override any backend/.env file."""

    def apply(**overrides):
        values = {
            "APP_MODE": "mock",
            "OPENAI_API_KEY": "",
            "GOOGLE_MAPS_API_KEY": "",
            "USAGE_LEDGER_PATH": str(tmp_path / "ledger.jsonl"),
            "PROJECT_BUDGET_THB": "4000",
            "PRIOR_SPEND_THB": "0",
            "MAX_RETRIES": "0",
        }
        values.update({k.upper(): str(v) for k, v in overrides.items()})
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        get_tracker.cache_clear()
        return get_settings()

    yield apply
    get_settings.cache_clear()
    get_tracker.cache_clear()


@pytest.fixture
def client(configure):
    configure()
    from app.main import app

    return TestClient(app)


def photo_bytes(size=(800, 600), color=(120, 130, 140), detail=True) -> bytes:
    image = Image.new("RGB", size, color)
    if detail:
        draw = ImageDraw.Draw(image)
        rng = random.Random(1)
        for _ in range(80):
            xy = [(rng.randint(0, size[0]), rng.randint(0, size[1])) for _ in range(2)]
            draw.line(xy, fill=(rng.randint(0, 255),) * 3, width=3)
    buf = io.BytesIO()
    image.save(buf, "JPEG")
    return buf.getvalue()


def upload(device_type: str, views=None, data=None):
    views = views if views is not None else list(REQUIRED_VIEWS[device_type])
    files = [("files", (f"{v}.jpg", data or photo_bytes(), "image/jpeg")) for v in views]
    return {"device_type": device_type, "views": views}, files


HEADERS = {"X-Assessment-Id": "test-assessment-0001"}
