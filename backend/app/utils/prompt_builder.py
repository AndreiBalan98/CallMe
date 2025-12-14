"""
Prompt builder for constructing OpenAI Realtime API instructions.
Builds dynamic prompts based on clinic data.
"""

import random
from typing import Dict, List, Any
from datetime import datetime, date


def build_system_prompt(
    clinic: Dict[str, Any],
    doctors: List[Dict[str, Any]],
    services: List[Dict[str, Any]],
    appointments: List[Dict[str, Any]],
    target_date: date
) -> str:
    """
    Build the system prompt for the AI assistant.
    
    Args:
        clinic: Clinic information
        doctors: List of doctors
        services: List of available services
        appointments: Existing appointments for the day
        target_date: The date for scheduling (today)
        
    Returns:
        Complete system prompt string.
    """
    
    # Pick a random greeting template
    greeting = random.choice(clinic.get("greeting_templates", [
        f"Bună ziua, {clinic['name']}, cu ce vă putem ajuta?"
    ]))
    
    # Format doctors info
    doctors_info = "\n".join([
        f"- {doc['name']} ({doc['specialization']}): {', '.join(doc['available_services'])}"
        for doc in doctors
    ])
    
    # Format services info
    services_info = "\n".join([
        f"- {svc['name']}: {svc['price']} RON ({svc['duration_minutes']} minute) - {svc['description']}"
        for svc in services
    ])
    
    # Calculate available slots per doctor
    working_hours = clinic.get("working_hours", {"start": "08:00", "end": "18:00"})
    slot_duration = clinic.get("working_hours", {}).get("slot_duration_minutes", 30)
    
    availability_info = _build_availability_info(
        doctors, appointments, target_date, working_hours, slot_duration
    )
    
    prompt = f"""Ești asistenta telefonică virtuală a clinicii dentare "{clinic['name']}".

SALUT INIȚIAL (folosește la începutul conversației):
"{greeting}"

INFORMAȚII CLINICĂ:
- Nume: {clinic['name']}
- Adresă: {clinic.get('address', 'N/A')}
- Telefon: {clinic.get('phone', 'N/A')}
- Program: {working_hours['start']} - {working_hours['end']}
- Durata unei programări: {slot_duration} minute

DOCTORI DISPONIBILI:
{doctors_info}

SERVICII ȘI TARIFE:
{services_info}

DISPONIBILITATE PENTRU AZI ({target_date.strftime('%d.%m.%Y')}):
{availability_info}

INSTRUCȚIUNI COMPORTAMENT:
1. Fii caldă, profesionistă și prietenoasă
2. Răspunde concis, nu mai mult de 2-3 propoziții pe răspuns
3. Dacă pacientul dorește o programare, colectează:
   - Serviciul dorit
   - Preferința de doctor (sau lasă-l să aleagă)
   - Ora preferată (propune ore disponibile)
   - Numele complet al pacientului
   - Numărul de telefon pentru confirmare
4. Când ai toate informațiile, folosește funcția create_appointment pentru a finaliza programarea
5. După programare, confirmă detaliile verbal
6. Dacă o oră nu este disponibilă, propune alternative
7. Nu inventa informații - folosește doar datele de mai sus
8. Dacă nu știi ceva, spune că vei verifica și să te sune din nou
9. La întrebări despre prețuri, fii transparentă cu tarifele
10. Poți fi întreruptă de pacient - adaptează-te natural

IMPORTANT:
- Data de azi este {target_date.strftime('%d.%m.%Y')}
- Programările se fac doar pentru azi
- Verifică disponibilitatea înainte de a confirma o oră
- Folosește funcția create_appointment DOAR când ai toate datele necesare
"""
    
    return prompt


def _build_availability_info(
    doctors: List[Dict],
    appointments: List[Dict],
    target_date: date,
    working_hours: Dict,
    slot_duration: int
) -> str:
    """Build availability string showing free/busy slots per doctor."""
    
    # Generate all time slots
    start_hour, start_min = map(int, working_hours["start"].split(":"))
    end_hour, end_min = map(int, working_hours["end"].split(":"))
    
    all_slots = []
    current_hour, current_min = start_hour, start_min
    
    while (current_hour < end_hour) or (current_hour == end_hour and current_min < end_min):
        all_slots.append(f"{current_hour:02d}:{current_min:02d}")
        current_min += slot_duration
        if current_min >= 60:
            current_hour += 1
            current_min = 0
    
    # Build availability per doctor
    availability_lines = []
    date_str = target_date.isoformat()
    
    for doctor in doctors:
        # Find appointments for this doctor today
        doctor_appointments = [
            apt for apt in appointments
            if apt.get("doctor_id") == doctor["id"] and apt.get("date") == date_str
        ]
        booked_times = {apt.get("time") for apt in doctor_appointments}
        
        free_slots = [slot for slot in all_slots if slot not in booked_times]
        
        if free_slots:
            # Show first 5 available slots to keep prompt concise
            slots_preview = ", ".join(free_slots[:5])
            more = f" (și alte {len(free_slots) - 5} ore)" if len(free_slots) > 5 else ""
            availability_lines.append(
                f"- {doctor['name']}: Ore libere: {slots_preview}{more}"
            )
        else:
            availability_lines.append(f"- {doctor['name']}: COMPLET pentru azi")
    
    return "\n".join(availability_lines)


def get_appointment_tool_definition() -> Dict:
    """
    Get the function/tool definition for creating appointments.
    Used in OpenAI Realtime API session configuration.
    """
    return {
        "type": "function",
        "name": "create_appointment",
        "description": "Creează o programare la clinica dentară. Folosește această funcție când pacientul dorește să facă o programare și ai colectat toate informațiile necesare: serviciu, doctor, oră, nume și telefon.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_id": {
                    "type": "string",
                    "description": "ID-ul doctorului ales (ex: dr-popescu, dr-ionescu, dr-dumitrescu)"
                },
                "time": {
                    "type": "string",
                    "description": "Ora programării în format HH:MM (ex: 10:00, 14:30)"
                },
                "patient_name": {
                    "type": "string",
                    "description": "Numele complet al pacientului"
                },
                "patient_phone": {
                    "type": "string",
                    "description": "Numărul de telefon al pacientului"
                },
                "service_id": {
                    "type": "string",
                    "description": "ID-ul serviciului dorit (ex: consultatie, detartraj, extractie)"
                }
            },
            "required": ["doctor_id", "time", "patient_name", "patient_phone", "service_id"]
        }
    }
