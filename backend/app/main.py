"""
Dental Voice Assistant - Main FastAPI Application
Real-time voice assistant for dental clinic appointment booking
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logging import setup_logging, get_logger
from app.routers import health, config, appointments, calls, websockets
from app.services.event_bus import event_bus

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    setup_logging()
    logger.info("=" * 60)
    logger.info("🦷 Dental Voice Assistant - Starting")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   Debug: {settings.debug}")
    logger.info(f"   Port: {settings.port}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("🦷 Dental Voice Assistant - Shutting down")
    await event_bus.shutdown()


app = FastAPI(
    title="Dental Voice Assistant",
    description="Real-time voice assistant for dental clinic appointment booking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(config.router, prefix="/api", tags=["Configuration"])
app.include_router(appointments.router, prefix="/api", tags=["Appointments"])
app.include_router(calls.router, tags=["Twilio Calls"])
app.include_router(websockets.router, tags=["WebSockets"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
