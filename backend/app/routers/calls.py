"""
Twilio call handling endpoints.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request) -> HTMLResponse:
    """
    Twilio webhook for incoming calls.
    Returns TwiML that connects the call to our WebSocket for media streaming.
    """
    # Get host for WebSocket URL
    host = request.url.hostname
    port_suffix = f":{request.url.port}" if request.url.port and request.url.port not in (80, 443) else ""
    
    # Determine protocol (ws or wss)
    protocol = "wss" if request.url.scheme == "https" else "ws"
    
    # TwiML response - connects call to our media stream WebSocket
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{protocol}://{host}{port_suffix}/media-stream" />
    </Connect>
</Response>"""
    
    logger.info(f"📞 Incoming call - connecting to {protocol}://{host}{port_suffix}/media-stream")
    
    return HTMLResponse(content=twiml, media_type="application/xml")


@router.post("/call-status")
async def call_status(request: Request) -> dict:
    """
    Twilio webhook for call status updates (optional).
    Can be used for tracking call lifecycle events.
    """
    form_data = await request.form()
    
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    
    logger.info(f"📊 Call status update - SID: {call_sid[:15]}... Status: {call_status}")
    
    return {"status": "received"}
