"""
Pydantic models for WebSocket events between backend and dashboard.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List, Literal
from pydantic import BaseModel, Field


# Event types for dashboard WebSocket communication
EventType = Literal[
    "call_started",
    "call_ended", 
    "transcript_user",
    "transcript_agent",
    "appointment_created",
    "appointment_updated",
    "appointment_deleted",
    "connection_status",
    "error"
]


class DashboardEvent(BaseModel):
    """Base event model for dashboard WebSocket communication."""
    type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)


class CallStartedEvent(DashboardEvent):
    """Event when a new call starts."""
    type: Literal["call_started"] = "call_started"
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "call_id": "",
            "caller_number": ""
        }
    )


class CallEndedEvent(DashboardEvent):
    """Event when a call ends."""
    type: Literal["call_ended"] = "call_ended"
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "call_id": "",
            "duration_seconds": 0
        }
    )


class TranscriptEvent(DashboardEvent):
    """Event for real-time transcription."""
    type: Literal["transcript_user", "transcript_agent"]
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "call_id": "",
            "text": "",
            "is_final": False
        }
    )


class AppointmentEvent(DashboardEvent):
    """Event for appointment changes."""
    type: Literal["appointment_created", "appointment_updated", "appointment_deleted"]
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "appointment": {}
        }
    )


class ConnectionStatusEvent(DashboardEvent):
    """Event for connection status updates."""
    type: Literal["connection_status"] = "connection_status"
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "status": "connected",  # connected, disconnected, reconnecting
            "message": ""
        }
    )


class ErrorEvent(DashboardEvent):
    """Event for error notifications."""
    type: Literal["error"] = "error"
    data: Dict[str, Any] = Field(
        default_factory=lambda: {
            "code": "",
            "message": ""
        }
    )


# Message from frontend to backend
class DashboardCommand(BaseModel):
    """Command from dashboard to backend."""
    command: Literal["subscribe", "unsubscribe", "ping"]
    data: Dict[str, Any] = Field(default_factory=dict)
