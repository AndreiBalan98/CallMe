"""
Configuration endpoints for clinic data.
"""

from datetime import date
from typing import List, Dict, Any
from fastapi import APIRouter

from app.utils.json_store import json_store
from app.services.appointment import appointment_service

router = APIRouter()


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """
    Get full clinic configuration including doctors, services, and today's schedule.
    Used by the dashboard to initialize.
    """
    clinic = await json_store.read("clinic.json")
    doctors = await json_store.read("doctors.json")
    services = await json_store.read("services.json")
    
    today = date.today().isoformat()
    appointments = await appointment_service.get_all(filter_date=today)
    
    return {
        "clinic": clinic,
        "doctors": doctors,
        "services": services,
        "appointments": appointments,
        "today": today
    }


@router.get("/config/clinic")
async def get_clinic() -> Dict[str, Any]:
    """Get clinic information."""
    return await json_store.read("clinic.json")


@router.get("/config/doctors")
async def get_doctors() -> List[Dict[str, Any]]:
    """Get list of doctors."""
    return await json_store.read("doctors.json")


@router.get("/config/services")
async def get_services() -> List[Dict[str, Any]]:
    """Get list of services."""
    return await json_store.read("services.json")


@router.get("/config/schedule/{doctor_id}")
async def get_doctor_schedule(doctor_id: str) -> Dict[str, Any]:
    """
    Get schedule for a specific doctor for today.
    Returns available and booked slots.
    """
    clinic = await json_store.read("clinic.json")
    doctors = await json_store.read("doctors.json")
    
    doctor = next((d for d in doctors if d["id"] == doctor_id), None)
    if not doctor:
        return {"error": "Doctor not found"}
    
    today = date.today().isoformat()
    working_hours = clinic.get("working_hours", {
        "start": "08:00",
        "end": "18:00",
        "slot_duration_minutes": 30
    })
    
    appointments = await appointment_service.get_by_doctor_and_date(doctor_id, today)
    available = await appointment_service.get_available_slots(
        doctor_id, today, working_hours
    )
    
    return {
        "doctor": doctor,
        "date": today,
        "working_hours": working_hours,
        "appointments": appointments,
        "available_slots": available
    }
