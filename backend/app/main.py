"""
FastAPI application factory.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .api import api_router
from .core.config import get_settings
from .core.logging import setup_logging

settings = get_settings()


def create_app() -> FastAPI:
    setup_logging(debug=settings.debug)
    logger.info("Starting AutoGrade Backend API")

    app = FastAPI(
        title="AutoGrade Backend",
        description=(
            "Automated answer sheet correction using "
            "OpenCV preprocessing → Google Cloud Vision OCR → Gemini AI grading"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error on {request.url}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": str(exc)},
        )

    # Include all routes
    app.include_router(api_router)

    @app.on_event("startup")
    async def startup():
        # Ensure upload dirs exist
        import os
        os.makedirs("uploads/raw", exist_ok=True)
        os.makedirs("uploads/processed", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        logger.success("AutoGrade API ready ✓")

    return app


app = create_app()
