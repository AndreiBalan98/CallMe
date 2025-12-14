"""
Pydantic models for doctors and services.
"""

from typing import List
from pydantic import BaseModel, Field


class Doctor(BaseModel):
    """Model for a doctor."""
    id: str
    name: str
    specialization: str
    available_services: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "dr-popescu",
                "name": "Dr. Maria Popescu",
                "specialization": "Ortodonție",
                "available_services": ["consultatie", "aparat-dentar", "gutiera"]
            }
        }


class Service(BaseModel):
    """Model for a dental service."""
    id: str
    name: str
    price: int
    duration_minutes: int
    description: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "consultatie",
                "name": "Consultație",
                "price": 100,
                "duration_minutes": 30,
                "description": "Consultație și plan de tratament"
            }
        }


class WorkingHours(BaseModel):
    """Model for working hours configuration."""
    start: str = "08:00"
    end: str = "18:00"
    slot_duration_minutes: int = 30


class Clinic(BaseModel):
    """Model for clinic information."""
    name: str
    phone: str
    address: str
    greeting_templates: List[str] = Field(default_factory=list)
    working_hours: WorkingHours = Field(default_factory=WorkingHours)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Clinica Dentară SmilePro",
                "phone": "+40 XXX XXX XXX",
                "address": "Str. Exemplu 123, București",
                "greeting_templates": [
                    "Bună ziua, Clinica SmilePro, cu ce vă putem ajuta?"
                ],
                "working_hours": {
                    "start": "08:00",
                    "end": "18:00",
                    "slot_duration_minutes": 30
                }
            }
        }
