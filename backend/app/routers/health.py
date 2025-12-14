"""
Health check endpoints.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import settings
from app.services.event_bus import event_bus

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic HTML status page."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dental Voice Assistant</title>
        <style>
            body { font-family: system-ui; max-width: 600px; margin: 50px auto; padding: 20px; }
            h1 { color: #2563eb; }
            .status { color: #16a34a; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🦷 Dental Voice Assistant</h1>
        <p>Status: <span class="status">Running</span></p>
        <p>Real-time voice assistant for dental clinic appointment booking.</p>
        <hr>
        <h3>Endpoints:</h3>
        <ul>
            <li><code>GET /health</code> - Health check</li>
            <li><code>GET /api/config</code> - Clinic configuration</li>
            <li><code>GET /api/appointments</code> - Today's appointments</li>
            <li><code>POST /incoming-call</code> - Twilio webhook</li>
            <li><code>WS /media-stream</code> - Twilio media stream</li>
            <li><code>WS /ws/dashboard</code> - Dashboard real-time updates</li>
        </ul>
    </body>
    </html>
    """)


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "dental-voice-assistant",
        "version": "1.0.0",
        "environment": settings.environment,
        "dashboard_connections": event_bus.subscriber_count
    }
