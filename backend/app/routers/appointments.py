"""
Appointments REST API endpoints.
"""

from datetime import date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.appointment import AppointmentCreate, Appointment, AppointmentResponse
from app.services.appointment import appointment_service

router = APIRouter()


@router.get("/appointments")
async def get_appointments(
    filter_date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)")
) -> List[Dict[str, Any]]:
    """
    Get all appointments, optionally filtered by date.
    If no date provided, returns today's appointments.
    """
    if filter_date is None:
        filter_date = date.today().isoformat()
    
    return await appointment_service.get_all(filter_date=filter_date)


@router.get("/appointments/{appointment_id}")
async def get_appointment(appointment_id: str) -> Dict[str, Any]:
    """Get a single appointment by ID."""
    appointment = await appointment_service.get_by_id(appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return appointment


@router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(data: AppointmentCreate) -> AppointmentResponse:
    """Create a new appointment from dashboard."""
    success, message, appointment = await appointment_service.create(
        doctor_id=data.doctor_id,
        target_date=data.date,
        time=data.time,
        patient_name=data.patient_name,
        patient_phone=data.patient_phone,
        service_id=data.service_id,
        created_by="dashboard"
    )
    
    return AppointmentResponse(
        success=success,
        message=message,
        appointment=Appointment(**appointment) if appointment else None
    )


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    updates: Dict[str, Any]
) -> AppointmentResponse:
    """Update an existing appointment."""
    success, message, appointment = await appointment_service.update(
        appointment_id, updates
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return AppointmentResponse(
        success=success,
        message=message,
        appointment=Appointment(**appointment) if appointment else None
    )


@router.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str) -> Dict[str, Any]:
    """Delete/cancel an appointment."""
    success, message = await appointment_service.delete(appointment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"success": success, "message": message}
