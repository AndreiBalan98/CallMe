"""
WebSocket endpoints for Twilio media stream and dashboard real-time updates.
"""

import uuid
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.logging import get_logger
from app.services.call_handler import CallHandler
from app.services.event_bus import event_bus

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams.
    Handles bidirectional audio streaming between Twilio and OpenAI.
    """
    await websocket.accept()
    logger.info("🔌 Twilio WebSocket connected")
    
    # Generate unique call ID
    call_id = str(uuid.uuid4())
    
    # Create call handler
    handler = CallHandler(call_id)
    
    try:
        await handler.handle_call(websocket)
    except WebSocketDisconnect:
        logger.info(f"📴 Twilio WebSocket disconnected - Call: {call_id[:8]}")
    except Exception as e:
        logger.error(f"❌ Error in media stream: {e}")
    finally:
        logger.info(f"🔌 Media stream closed - Call: {call_id[:8]}")


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard real-time updates.
    Sends call events, transcriptions, and appointment updates.
    """
    await websocket.accept()
    logger.info("📊 Dashboard WebSocket connected")
    
    # Subscribe to events
    queue = await event_bus.subscribe()
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_status",
            "data": {
                "status": "connected",
                "message": "Connected to dashboard WebSocket"
            }
        })
        
        # Handle both incoming messages and outgoing events
        receive_task = asyncio.create_task(_handle_dashboard_receive(websocket))
        send_task = asyncio.create_task(_handle_dashboard_send(websocket, queue))
        
        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    except WebSocketDisconnect:
        logger.info("📊 Dashboard WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ Error in dashboard WebSocket: {e}")
    finally:
        await event_bus.unsubscribe(queue)
        logger.info("📊 Dashboard WebSocket closed")


async def _handle_dashboard_receive(websocket: WebSocket) -> None:
    """Handle incoming messages from dashboard."""
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            command = message.get("command", "")
            
            if command == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "data": {}
                })
            # Add more commands as needed
            
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"Error receiving dashboard message: {e}")


async def _handle_dashboard_send(websocket: WebSocket, queue: asyncio.Queue) -> None:
    """Send events from queue to dashboard."""
    try:
        while True:
            event = await queue.get()
            
            # Check for shutdown signal
            if event.get("type") == "shutdown":
                break
            
            await websocket.send_json(event)
            
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"Error sending dashboard event: {e}")
