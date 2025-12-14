"""
Appointment service for managing dental appointments.
Handles CRUD operations and validation.
"""

import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple

from app.utils.logging import get_logger
from app.utils.json_store import json_store
from app.services.event_bus import event_bus

logger = get_logger(__name__)


class AppointmentService:
    """Service for managing appointments."""
    
    APPOINTMENTS_FILE = "appointments.json"
    
    async def get_all(self, filter_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all appointments, optionally filtered by date.
        
        Args:
            filter_date: Optional date string (YYYY-MM-DD) to filter by.
            
        Returns:
            List of appointments.
        """
        appointments = await json_store.read(self.APPOINTMENTS_FILE)
        
        if filter_date:
            appointments = [
                apt for apt in appointments 
                if apt.get("date") == filter_date
            ]
        
        return appointments
    
    async def get_by_id(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """Get a single appointment by ID."""
        appointments = await json_store.read(self.APPOINTMENTS_FILE)
        
        for apt in appointments:
            if apt.get("id") == appointment_id:
                return apt
        
        return None
    
    async def get_by_doctor_and_date(
        self, 
        doctor_id: str, 
        target_date: str
    ) -> List[Dict[str, Any]]:
        """Get all appointments for a specific doctor on a specific date."""
        appointments = await json_store.read(self.APPOINTMENTS_FILE)
        
        return [
            apt for apt in appointments
            if apt.get("doctor_id") == doctor_id and apt.get("date") == target_date
        ]
    
    async def is_slot_available(
        self, 
        doctor_id: str, 
        target_date: str, 
        time: str
    ) -> bool:
        """Check if a time slot is available for a doctor."""
        doctor_appointments = await self.get_by_doctor_and_date(doctor_id, target_date)
        booked_times = {apt.get("time") for apt in doctor_appointments}
        return time not in booked_times
    
    async def create(
        self,
        doctor_id: str,
        target_date: str,
        time: str,
        patient_name: str,
        patient_phone: str,
        service_id: str,
        created_by: str = "ai-assistant"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new appointment.
        
        Returns:
            Tuple of (success, message, appointment_or_none)
        """
        # Validate slot availability
        if not await self.is_slot_available(doctor_id, target_date, time):
            return (
                False, 
                f"Ora {time} nu este disponibilă pentru acest doctor.", 
                None
            )
        
        # Create appointment
        appointment = {
            "id": f"apt-{uuid.uuid4().hex[:8]}",
            "doctor_id": doctor_id,
            "date": target_date,
            "time": time,
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "service_id": service_id,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
            "status": "confirmed"
        }
        
        # Save to store
        await json_store.append_to_list(self.APPOINTMENTS_FILE, appointment)
        
        # Broadcast event to dashboard
        await event_bus.publish_appointment_created(appointment)
        
        logger.info(f"Created appointment {appointment['id']} for {patient_name} at {time}")
        
        return (True, "Programare creată cu succes!", appointment)
    
    async def update(
        self,
        appointment_id: str,
        updates: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update an existing appointment.
        
        Returns:
            Tuple of (success, message, appointment_or_none)
        """
        # Don't allow changing ID
        updates.pop("id", None)
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        appointment = await json_store.update_in_list(
            self.APPOINTMENTS_FILE,
            appointment_id,
            updates
        )
        
        if appointment:
            await event_bus.publish_appointment_updated(appointment)
            logger.info(f"Updated appointment {appointment_id}")
            return (True, "Programare actualizată!", appointment)
        
        return (False, "Programarea nu a fost găsită.", None)
    
    async def delete(self, appointment_id: str) -> Tuple[bool, str]:
        """
        Delete an appointment.
        
        Returns:
            Tuple of (success, message)
        """
        deleted = await json_store.delete_from_list(
            self.APPOINTMENTS_FILE,
            appointment_id
        )
        
        if deleted:
            await event_bus.publish_appointment_deleted(appointment_id)
            logger.info(f"Deleted appointment {appointment_id}")
            return (True, "Programare anulată!")
        
        return (False, "Programarea nu a fost găsită.")
    
    async def get_available_slots(
        self,
        doctor_id: str,
        target_date: str,
        working_hours: Dict[str, Any]
    ) -> List[str]:
        """
        Get all available time slots for a doctor on a date.
        
        Args:
            doctor_id: Doctor ID
            target_date: Date string (YYYY-MM-DD)
            working_hours: Dict with start, end, slot_duration_minutes
            
        Returns:
            List of available time strings (HH:MM)
        """
        # Generate all slots
        start_hour, start_min = map(int, working_hours["start"].split(":"))
        end_hour, end_min = map(int, working_hours["end"].split(":"))
        slot_duration = working_hours.get("slot_duration_minutes", 30)
        
        all_slots = []
        current_hour, current_min = start_hour, start_min
        
        while (current_hour < end_hour) or (current_hour == end_hour and current_min < end_min):
            all_slots.append(f"{current_hour:02d}:{current_min:02d}")
            current_min += slot_duration
            if current_min >= 60:
                current_hour += 1
                current_min = 0
        
        # Get booked slots
        appointments = await self.get_by_doctor_and_date(doctor_id, target_date)
        booked_times = {apt.get("time") for apt in appointments}
        
        # Return free slots
        return [slot for slot in all_slots if slot not in booked_times]


# Global service instance
appointment_service = AppointmentService()
