# FastAPI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Internal -- database
from database import Base, engine

# Internal -- routers
from routes.audio_routes import router as audio_router
from routes.auth_routes import router as auth_router
from routes.diagnosis_routes import router as diagnosis_router
from routes.progression_routes import router as progression_router
from routes.report_routes import router as report_router
from routes.severity_routes import router as severity_router
from routes.treatment_routes import router as treatment_router


# ---------------------------------------------------------------------------
# APPLICATION INSTANCE
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Parkinson's Audio-Based Monitoring API",
    description=(
        "Backend API for Parkinson's disease monitoring and management."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------------------
#
# Creates all database tables on application startup if they do not exist.
#
# NOTE:
# In production environments, Alembic migrations are strongly recommended
# instead of automatic table creation.
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup() -> None:
    """
    Initialize database tables during application startup.
    """
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------------------------------------
#
# DEVELOPMENT:
#   Currently allows all origins for easier frontend integration.
#
# PRODUCTION:
#   Replace '*' with explicit frontend domains.
#
# Example:
#
#   allow_origins=[
#       "http://localhost:3000",
#       "https://yourdomain.com",
#   ]
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API VERSION PREFIX
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"


# ---------------------------------------------------------------------------
# ROUTER REGISTRATION
# ---------------------------------------------------------------------------
#
# API modules are registered here.
#
# ROUTE PREFIXES:
#   /api/v1/auth
#   /api/v1/audio
#   /api/v1/diagnosis
#   /api/v1/progression
#   /api/v1/report
#   /api/v1/severity
#   /api/v1/treatment
# ---------------------------------------------------------------------------

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(audio_router, prefix=API_PREFIX)
app.include_router(diagnosis_router, prefix=API_PREFIX)
app.include_router(progression_router, prefix=API_PREFIX)
app.include_router(report_router, prefix=API_PREFIX)
app.include_router(severity_router, prefix=API_PREFIX)
app.include_router(treatment_router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# ROOT HEALTH ENDPOINT
# ---------------------------------------------------------------------------
#
# Basic API health/status endpoint.
#
# Can later be extended to include:
#   - database connectivity checks
#   - background worker status
#   - ML service availability
#   - queue monitoring
# ---------------------------------------------------------------------------

@app.get(
    "/",
    status_code=200,
    summary="API health check",
    tags=["Health"],
)
def root() -> dict[str, str]:
    """
    Basic API health check endpoint.
    """
    return {
        "message": (
            "Parkinson's Audio-Based Monitoring API is running."
        )
    }


# ---------------------------------------------------------------------------
# FUTURE ML INTEGRATION POINT
# ---------------------------------------------------------------------------
#
# Future ML integrations may include:
#
#   # TODO: Register ML prediction services
#   # TODO: Add background task queue integration
#   # TODO: Add automated audio analysis pipeline
#   # TODO: Add model inference endpoints
#
# ML components are intentionally excluded from this backend-only version.
# ---------------------------------------------------------------------------