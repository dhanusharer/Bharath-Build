import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import health
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.schemas.error import ErrorBody, ErrorResponse

logger = logging.getLogger("medication_accessibility")
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management for setup and teardown."""
    logger.info("Initializing %s in %s environment...", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=(
        "Production API for Multimodal Medication Accessibility System. "
        "Digitizes handwritten prescriptions with safety-first deterministic validation."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Inject and propagate X-Request-ID correlation identifier."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ensure all unhandled exceptions adhere to standard API contract error envelope."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    logger.error("Unhandled exception for request %s: %s", request_id, str(exc), exc_info=True)

    error_payload = ErrorResponse(
        error=ErrorBody(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please retry later.",
            details=[],
            request_id=request_id,
            safe_action_required="CONSULT_PHARMACIST",
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(mode="json"),
    )


# Root probe endpoints for container health checks
app.include_router(health.router)

# Versioned API routes
app.include_router(api_v1_router, prefix="/api/v1")
