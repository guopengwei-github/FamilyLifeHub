"""
FamilyLifeHub Backend - Main Application Entry Point

A private family life data hub for tracking health and work metrics.
"""
import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import ingest, dashboard, users, auth, health, garmin, preferences, timeseries, reports, smtp_config, scheduler_logs

# Run database migrations before creating tables
from migrations.add_sleep_stage_columns import migrate as migrate_sleep_stages

print("Running database migrations...")
migrate_sleep_stages()
print("Migrations completed.")

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Private family life data hub for health and work tracking",
    version="1.0.0",
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
uploads_path = Path(__file__).parent / "uploads"
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# Include API routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(health.router, prefix="/api/v1")
app.include_router(garmin.router, prefix="/api/v1")
app.include_router(preferences.router, prefix="/api/v1")
app.include_router(timeseries.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(smtp_config.router, prefix="/api/v1")
app.include_router(scheduler_logs.router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    """Initialize scheduler on application startup."""
    if not settings.scheduler_enabled:
        return


    from app.tasks.scheduler import start_scheduler
    logger.info("Scheduler started on application startup")
    start_scheduler()
