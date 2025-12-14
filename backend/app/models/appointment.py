"""
Pydantic models for appointments.
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    """Model for creating a new appointment."""
    doctor_id: str = Field(..., description="ID of the doctor")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in HH:MM format")
    patient_name: str = Field(..., description="Patient's full name")
    patient_phone: str = Field(..., description="Patient's phone number")
    service_id: str = Field(..., description="ID of the service")
    
    class Config:
        json_schema_extra = {
            "example": {
                "doctor_id": "dr-popescu",
                "date": "2024-12-14",
                "time": "10:00",
                "patient_name": "Ion Popescu",
                "patient_phone": "+40722123456",
                "service_id": "consultatie"
            }
        }


class Appointment(BaseModel):
    """Full appointment model including generated fields."""
    id: str
    doctor_id: str
    date: str
    time: str
    patient_name: str
    patient_phone: str
    service_id: str
    created_at: str
    created_by: str = "ai-assistant"
    status: str = "confirmed"
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "apt-001",
                "doctor_id": "dr-popescu",
                "date": "2024-12-14",
                "time": "10:00",
                "patient_name": "Ion Popescu",
                "patient_phone": "+40722123456",
                "service_id": "consultatie",
                "created_at": "2024-12-14T09:30:00Z",
                "created_by": "ai-assistant",
                "status": "confirmed"
            }
        }


class AppointmentResponse(BaseModel):
    """Response model for appointment operations."""
    success: bool
    message: str
    appointment: Optional[Appointment] = None
