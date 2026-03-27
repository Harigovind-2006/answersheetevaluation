"""
Health check and diagnostics endpoint.
"""

from pathlib import Path

from fastapi import APIRouter
from loguru import logger
import cv2

from ...core.config import get_settings
from ...models.schemas import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check():
    """Check if the service and all dependencies are operational."""
    services = {}

    # Check OpenCV
    try:
        _ = cv2.__version__
        services["opencv"] = True
    except Exception:
        services["opencv"] = False

    # Check Gemini API key present
    services["gemini_api_key_set"] = bool(settings.gemini_api_key)

    # Check OpenAI API key present
    services["openai_api_key_set"] = bool(settings.openai_api_key)

    # Check Supabase credentials
    services["supabase_configured"] = bool(settings.supabase_url and settings.supabase_key)

    # Upload dirs
    import os
    services["upload_dirs"] = (
        os.path.isdir("uploads/raw") and os.path.isdir("uploads/processed")
    )

    all_ok = all(services.values())

    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        version="1.0.0",
        services=services,
    )


@router.get("/", summary="Root")
async def root():
    return {
        "name": "AutoGrade Backend API",
        "version": "1.0.0",
        "description": "Automated answer sheet correction: OpenCV → Cloud Vision → Gemini",
        "docs": "/docs",
    }
