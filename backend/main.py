"""
FamilyLifeHub Backend - Main Application Entry Point

A private family life data hub for tracking health and work metrics.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import ingest, dashboard, users, auth, health, garmin, strava, preferences

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

# Include API routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(health.router, prefix="/api/v1")
app.include_router(garmin.router, prefix="/api/v1")
app.include_router(strava.router, prefix="/api/v1")
app.include_router(preferences.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "FamilyLifeHub API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
