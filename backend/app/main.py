"""FastAPI entry point. Run with: uvicorn app.main:app --reload --port 8000"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import assessment, results, system

# Request bodies (photos, locations, findings) are never logged.
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

settings = get_settings()
app = FastAPI(title="E-waste Sorter API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Assessment-Id", "X-Mock-Scenario"],
)
app.include_router(system.router)
app.include_router(assessment.router)
app.include_router(results.router)

logging.getLogger(__name__).info("E-waste Sorter backend started in %s mode", settings.app_mode)
