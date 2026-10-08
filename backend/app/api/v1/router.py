from fastapi import APIRouter

from app.api.v1.endpoints import digital_twin, health, prescriptions, voice

api_v1_router = APIRouter()

# Include health routes
api_v1_router.include_router(health.router)

# Include prescriptions routes
api_v1_router.include_router(prescriptions.router)

# Include voice accessibility routes
api_v1_router.include_router(voice.router)

# Include digital twin routes
api_v1_router.include_router(digital_twin.router)

