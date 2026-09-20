from fastapi import APIRouter

from app.api.v1.endpoints import health, prescriptions, voice

api_v1_router = APIRouter()

# Include health routes
api_v1_router.include_router(health.router)

# Include prescriptions routes
api_v1_router.include_router(prescriptions.router)

# Include voice accessibility routes
api_v1_router.include_router(voice.router)
