"""
Main FastAPI application entrypoint.
Registers all routers and manages the APScheduler background jobs.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import get_settings

# Import all models so SQLAlchemy knows about them (used by Alembic and relationships).
import models

# Import routers
from routers import (
    auth, service_center, advisory_case, users,
    service_request, product_request, broadcast, weather_alert, stats, sync,
    satellite_data,
)
from jobs.cycle_generator import run_cycle_generator
from jobs.weather_ingestion import run_weather_ingestion
from services.sync_service import run_sync

settings = get_settings()

# Initialize scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    
    # Schema creation is handled by Alembic migrations (alembic upgrade head)
    # which runs in entrypoint.sh before the server starts.
    
    # Register jobs
    # Cycle generator: every 5 days. For testing, we might want this manual or daily.
    scheduler.add_job(run_cycle_generator, 'interval', days=5, id='cycle_gen')
    
    # Weather ingestion: hourly
    scheduler.add_job(run_weather_ingestion, 'interval', hours=1, id='weather_ingest')
    
    # Agriverse DB Sync
    scheduler.add_job(run_sync, 'interval', minutes=settings.SYNC_INTERVAL_MINUTES, id='agriverse_sync')
    
    scheduler.start()
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(
    title="FAMS API",
    description="Backend for the Farm Advisory Management System (FAMS)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS config. Auth is a localStorage Bearer token (not cookies), so credentials
# are not needed — keeping allow_credentials False makes the "*" origin valid and
# avoids the insecure "*" + credentials combination browsers reject anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(service_center.router, prefix="/api")
app.include_router(advisory_case.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(service_request.router, prefix="/api")
app.include_router(product_request.router, prefix="/api")
app.include_router(broadcast.router, prefix="/api")
app.include_router(weather_alert.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(satellite_data.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
