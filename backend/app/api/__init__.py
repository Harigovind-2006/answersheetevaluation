from fastapi import APIRouter
from .routes import pipeline_router, health_router, export_router, auth_router

api_router = APIRouter()

api_router.include_router(pipeline_router)
api_router.include_router(health_router)
api_router.include_router(export_router)
api_router.include_router(auth_router)
